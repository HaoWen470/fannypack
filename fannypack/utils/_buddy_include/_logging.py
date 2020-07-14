from __future__ import annotations

import abc
import contextlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Generator, List, Optional, Union, cast

import numpy as np
import torch.utils.tensorboard

from .. import _deprecation
from ._optimizer import _BuddyOptimizer

if TYPE_CHECKING:
    from .._buddy import Buddy


class _BuddyLogging(abc.ABC):
    """Buddy's TensorBoard logging interface.
    """

    def __init__(self, log_dir: str) -> None:
        """Logging-specific setup.

        Args:
            log_dir (str): Path to save Tensorboard logs to.
        """
        self._log_dir = log_dir

        # Backwards-compatibility for deprecated API
        self.log = _deprecation.new_name_wrapper(
            "Buddy.log()", "Buddy.log_scalar()", self.log_scalar
        )

        # State variables for TensorBoard
        # Note that the writer is lazily instantiated; see below
        self._log_writer: Optional[torch.utils.tensorboard.SummaryWriter] = None
        self._log_scopes: List[str] = []

    @contextlib.contextmanager
    def log_scope(self, scope: str) -> Generator[None, None, None]:
        """Returns a context manager that scopes log names.

        Example usage:

        ```
            with buddy.log_scope("scope"):
                # Logs to scope/loss
                buddy.log_scalar("loss", loss_tensor)
        ```

        Args:
            scope (str): Name of scope.
        """
        self.log_scope_push(scope)
        yield
        self.log_scope_pop(scope)

    def log_scope_push(self, scope: str) -> None:
        """Push a scope to log tensors into.

        Example usage:
        ```
            buddy.log_scope_push("scope")

            # Logs to scope/loss
            buddy.log_scalar("loss", loss_tensor)

            buddy.log_scope_pop("scope") # name parameter is optional

        Args:
            scope (str): Name of scope.
        ```
        """
        self._log_scopes.append(scope)

    def log_scope_pop(self, scope: str = None) -> None:
        """Pop a scope we logged tensors into. See `log_scope_push()`.

        Args:
            scope (str, optional): Name of scope. Needs to be the top one in the stack.
        """
        popped = self._log_scopes.pop()
        if scope is not None:
            assert popped == scope, f"{popped} does not match {scope}!"

    def log_image(
        self,
        name: str,
        image: Union[torch.Tensor, np.ndarray],
        dataformats: str = "CHW",
    ) -> None:
        """Convenience function for logging an image tensor for visualization in
        TensorBoard.

        Equivalent to:
        ```
        buddy.log_writer.add_image(
            buddy.log_scope_prefix(name),
            image,
            buddy.optimizer_steps,
            dataformats
        )
        ```

        Args:
            name (str): Identifier for Tensorboard.
            image (torch.Tensor or np.ndarray): Image to log.
            dataformats (str, optional): Dimension ordering. Defaults to "CHW".
        """
        # Add scope prefixes
        name = self.log_scope_prefix(name)

        # Log scalar
        optimizer_steps = cast(_BuddyOptimizer, self).optimizer_steps
        self.log_writer.add_image(
            name, image, global_step=optimizer_steps, dataformats=dataformats
        )

    def log_scalar(
        self, name: str, value: Union[torch.Tensor, np.ndarray, float]
    ) -> None:
        """Convenience function for logging a scalar for visualization in TensorBoard.

        Equivalent to:
        ```
        buddy.log_writer.add_scalar(
            buddy.log_scope_prefix(name),
            value,
            buddy.optimizer_steps
        )
        ```

        Args:
            name (str): Identifier for Tensorboard.
            value (torch.Tensor, np.ndarray, or float): Value to log.
        """
        # Add scope prefixes
        name = self.log_scope_prefix(name)

        # Log scalar
        optimizer_steps = cast(_BuddyOptimizer, self).optimizer_steps
        self.log_writer.add_scalar(name, value, global_step=optimizer_steps)

    def log_model_weights_hist(self, name: str = "") -> None:
        """Logging model weights into histogram.


        Args:
            name (str, optional): Name to prepend a prefix to. Defaults to an empty string.
        """
        optimizer_steps = cast(_BuddyOptimizer, self).optimizer_steps

        for layer_name, p in self._model.named_parameters():
            if p.grad is None:
                continue

            layer_name = layer_name.replace(".", "/")
            self.log_writer.add_histogram(
                tag="{}weights/{}".format(self.log_scope_prefix(name), layer_name),
                values=p.data.detach().cpu().numpy(),
                global_step=optimizer_steps,
            )

    def log_model_grad_norm(self, name: str = "") -> None:
        """Logging model gradient norm


                Args:
                    name (str, optional): Name to prepend a prefix to. Defaults to an empty string.
                """
        optimizer_steps = cast(_BuddyOptimizer, self).optimizer_steps

        for layer_name, p in self._model.named_parameters():
            if p.grad is None:
                continue

            layer_name = layer_name.replace(".", "/")
            self.log_writer.add_scalar(
                "grad_norm/{}/{}".format(self.log_scope_prefix(name), layer_name),
                p.grad.data.norm(2).item(),
                optimizer_steps,
            )


    def log_model_grad_hist(self, name: str = "") -> None:
        """Logging model gradients into histogram.


        Args:
            name (str, optional): Name to prepend a prefix to. Defaults to an empty string.
        """
        optimizer_steps = cast(_BuddyOptimizer, self).optimizer_steps

        for layer_name, p in self._model.named_parameters():
            if p.grad is None:
                continue

            layer_name = layer_name.replace(".", "/")
            self.log_writer.add_histogram(
                tag="{}grad/{}".format(self.log_scope_prefix(name), layer_name),
                values=p.grad.detach().cpu().numpy(),
                global_step=optimizer_steps,
            )

    def log_scope_prefix(self, name: str = "") -> str:
        """Get or apply the current log scope prefix.

        Example usage:
        ```
        print(buddy.log_scope_prefix()) # ""

        with buddy.log_scope("scope0"):
            print(buddy.log_scope_prefix("loss")) # "scope0/loss"

            with buddy.log_scope("scope1"):
                print(buddy.log_scope_prefix()) # "scope0/scope1/"
        ```

        Args:
            name (str, optional): Name to prepend a prefix to. Defaults to an empty string.

        Returns:
            str: Scoped log name, or scope prefix if input is empty.
        """
        if len(self._log_scopes) == 0:
            return name
        else:
            return "{}/{}".format("/".join(self._log_scopes), name)

    @property
    def log_writer(self) -> torch.utils.tensorboard.SummaryWriter:
        """Accessor for standard Tensorboard SummaryWriter. Instantiated lazily.
        """
        if self._log_writer is None:
            self._log_writer = torch.utils.tensorboard.SummaryWriter(
                self._log_dir + "/" + cast("Buddy", self)._experiment_name
            )
        return self._log_writer
