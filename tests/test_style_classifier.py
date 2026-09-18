# test_style_classifier.py
import pytest

from tonofdevelopervoice.evaluate.style_classifier import StyleClassifier

AUTHENTIC_TEXTS = [
    "fix null pointer dereference in handler",
    "add config directive for timeout",
    "spi: fix clamping of max_speed_hz",
    "doc: fix typo in sphinx guide",
    "revert broken commit for gcc warning",
    "net: fix use-after-free in socket close",
    "mm: fix off-by-one in page allocator",
    "fs: fix race in inode cache",
    "drm: fix null deref on unbind",
    "usb: fix leak in error path",
    "arm64: dts: enable spi on baseboard",
    "block: fix double completion of request",
] * 3

SYNTHETIC_TEXTS = [
    (
        "I've made the following changes to address the null pointer issue in the "
        "handler function. Here's a summary of what was updated: I added a check."
    ),
    (
        "This commit addresses a bug where the config directive for the timeout "
        "setting was not being applied correctly. Let me know if you have questions."
    ),
    (
        "I noticed that the max_speed_hz clamping logic had an issue, so I went "
        "ahead and fixed it. I hope this resolves the problem you were seeing."
    ),
    (
        "I've gone through the sphinx documentation and corrected a typo I found. "
        "This should improve the readability of the docs going forward."
    ),
    (
        "This commit reverts a previous change that was causing a gcc warning to "
        "be emitted during the build process. I've verified this resolves it."
    ),
    (
        "I identified and fixed a use-after-free vulnerability in the socket close "
        "path. This was a subtle bug that could lead to memory corruption."
    ),
    (
        "I've updated the page allocator to fix an off-by-one error that was "
        "present in the previous implementation. Please review when you get a chance."
    ),
    (
        "This change fixes a race condition in the inode cache that could occur "
        "under certain concurrent access patterns. I've added appropriate locking."
    ),
    (
        "I fixed a null dereference that occurred during the unbind path in the "
        "drm driver. This should prevent the crash you reported."
    ),
    (
        "I've addressed a memory leak that was happening in the error handling "
        "path of the usb driver. Thanks for reporting this issue."
    ),
    (
        "I enabled SPI support at the baseboard level for the arm64 device tree, "
        "as this seemed like the most appropriate place to configure it."
    ),
    (
        "This commit fixes an issue where a block request could be completed "
        "twice under certain error conditions. I've added a guard to prevent this."
    ),
] * 3


def test_fit_returns_reasonable_held_out_accuracy() -> None:
    classifier = StyleClassifier()
    result = classifier.fit(AUTHENTIC_TEXTS, SYNTHETIC_TEXTS)
    assert 0.5 <= result.held_out_accuracy <= 1.0


def test_score_ranks_authentic_higher_than_synthetic() -> None:
    classifier = StyleClassifier()
    classifier.fit(AUTHENTIC_TEXTS, SYNTHETIC_TEXTS)

    authentic_score = classifier.score("fix double free in cleanup path")
    synthetic_score = classifier.score(
        "I've made the following changes to fix a double free issue I found in the "
        "cleanup path. Let me know if you'd like me to explain further."
    )

    assert authentic_score > synthetic_score


def test_score_before_fit_raises() -> None:
    classifier = StyleClassifier()
    with pytest.raises(RuntimeError, match="fit"):
        classifier.score("fix bug")
