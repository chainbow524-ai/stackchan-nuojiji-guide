"""Keep temporary public-avatar expressions uninterrupted by idle blink frames."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path

BOARD = "main/boards/stackchan/stackchan.cc"
ART = "main/boards/stackchan/avatar_images.local.cc"
OLD_SHA = "8cfec237290fc5d820e2072ac493670c670670de317155062d5c8131601a6056"
PUBLIC_ART_SHA = "754297290a71cc56db66d2294f6c537a933cca76735c1c6a2fbafede725d6166"
MARKER = "QIANMO_IDLE_ONLY_BLINK_V1"

def sha(data):
    return hashlib.sha256(data).hexdigest()

def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError("Unexpected source layout; no files changed")
    return text.replace(old, new, 1)

def patch(text):
    text = once(text,
        "        current_avatar_face_ = face;\n        if (avatar_face_timeout_timer_ != nullptr) {",
        """        current_avatar_face_ = face;
        // QIANMO_IDLE_ONLY_BLINK_V1: keep the full temporary expression
        // visible; idle eye frames belong to the idle face only.
        // The display lock also serializes this with both blink callbacks.
        if (idx != 0) {
            if (blink_step_timer_ != nullptr) {
                esp_timer_stop(blink_step_timer_);
            }
            blink_state_ = BlinkState::IDLE;
        }
        if (avatar_face_timeout_timer_ != nullptr) {""")
    text = once(text,
        "        DisplayLockGuard lock(display_);\n        switch (blink_state_) {",
        """        DisplayLockGuard lock(display_);
        // A queued blink callback must not repaint a new temporary face.
        if (current_avatar_face_ != "idle") {
            blink_state_ = BlinkState::IDLE;
            return;
        }
        switch (blink_state_) {""")
    text = once(text,
        """            current_eyes_index_ = 1;  // half
            active_layer_ = ActiveLayer::EYES;
            if (RenderAvatarLocked()) {
                blink_state_ = BlinkState::EYES_HALF_DOWN;
                esp_timer_start_once(blink_step_timer_, BLINK_STEP_MS * 1000);
            }
        }
        // Re-arm scheduler""",
        """            // Read the face under the same lock as expression changes.
            // Skip this blink during temporary expressions without changing
            // the user's blink setting or the regular scheduler cadence.
            if (current_avatar_face_ == "idle") {
                current_eyes_index_ = 1;  // half
                active_layer_ = ActiveLayer::EYES;
                if (RenderAvatarLocked()) {
                    blink_state_ = BlinkState::EYES_HALF_DOWN;
                    esp_timer_start_once(blink_step_timer_, BLINK_STEP_MS * 1000);
                }
            }
        }
        // Re-arm scheduler""")
    return text

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path.home()/"stackchan-public-build")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    source = args.source.resolve()
    board = source/BOARD
    if sha((source/ART).read_bytes()) != PUBLIC_ART_SHA:
        raise SystemExit("STOP: expected public geometric avatar; no files changed")
    original = board.read_bytes()
    text = original.decode("utf-8")
    if MARKER in text:
        raise SystemExit("Already patched; no files changed")
    if sha(original) != OLD_SHA:
        raise SystemExit("STOP: source differs from verified qianmo.2; no files changed")
    updated = patch(text).encode("utf-8")
    if args.dry_run:
        print("CHECK PASSED: public source and geometric avatar match; no files changed.")
        return
    backup = Path.home()/"stackchan-display-backup"/datetime.now().strftime("%Y%m%d-%H%M%S-idle-only-blink")
    target = backup/BOARD
    target.parent.mkdir(parents=True, exist_ok=False)
    target.write_bytes(original)
    (backup/"backup.json").write_text(json.dumps({"source":str(source), "file":BOARD,
        "before":sha(original), "after":sha(updated), "avatar_sha256":PUBLIC_ART_SHA}, indent=2), encoding="utf-8")
    temporary = board.with_name(board.name+".idle-blink.tmp")
    try:
        temporary.write_bytes(updated)
        os.replace(temporary, board)
    finally:
        if temporary.exists():
            temporary.unlink()
    print("PATCHED:", source)
    print("BACKUP:", backup)
    print("Blink only during idle; temporary faces keep their 5-second hold.")
    print("Subtitles remain 8 seconds. Avatar assets and blink preference preserved.")
    print("Nothing was compiled, flashed or restarted.")

if __name__ == "__main__":
    main()
