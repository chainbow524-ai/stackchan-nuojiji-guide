#!/usr/bin/env python3
"""Private StackChan display fix: isolated source patch, no flashing/restarts.
Preserves avatar art, networking, camera settings and all unrelated files.
"""
import argparse
from pathlib import Path
import re, shutil, hashlib, json, sys
from datetime import datetime

MARKER = "QIANMO_DISPLAY_TIMING_V1"

def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError("Source does not match expected anchor: " + old[:90])
    return text.replace(old, new, 1)

def function_region(text, signature):
    matches = [m.start() for m in re.finditer(re.escape(signature), text)]
    if len(matches) == 2 and signature in (
            "void LcdDisplay::SetChatMessage(", "void LcdDisplay::ClearChatMessages(",
            "void LcdDisplay::SetPreviewImage("):
        boundary = "#else\nvoid LcdDisplay::SetupUI()"
        if text.count(boundary) != 1:
            raise ValueError("Unknown chat UI layout")
        matches = [i for i in matches if i > text.index(boundary)]
    if len(matches) != 1:
        raise ValueError("Expected one function in supported UI mode: " + signature)
    start = matches[0]
    opening = text.index("{", start)
    masked = re.sub(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'',
                    lambda m: " " * len(m.group()), text, flags=re.S)
    depth = 0
    for i in range(opening, len(masked)):
        if masked[i] == "{": depth += 1
        elif masked[i] == "}":
            depth -= 1
            if depth == 0: return start, i + 1
    raise ValueError("Unbalanced function: " + signature)

def modify_function(text, signature, transform):
    a, b = function_region(text, signature)
    return text[:a] + transform(text[a:b]) + text[b:]

OVERLAY_FUNCTIONS = r'''
// QIANMO_DISPLAY_TIMING_V1: called only while the LVGL/display lock is held.
void LcdDisplay::RestoreStackChanOverlayOrderLocked() {
    if (preview_image_ != nullptr &&
        !lv_obj_has_flag(preview_image_, LV_OBJ_FLAG_HIDDEN)) {
        lv_obj_move_foreground(preview_image_);
    }
    if (bottom_bar_ != nullptr &&
        !lv_obj_has_flag(bottom_bar_, LV_OBJ_FLAG_HIDDEN)) {
        lv_obj_move_foreground(bottom_bar_);
    }
}

void LcdDisplay::ArmSubtitleTimeoutLocked() {
    // LVGL timers and message updates share the LVGL lock. Resetting this
    // timer cannot leave an older queued callback that hides a newer message.
    if (subtitle_timeout_timer_ == nullptr) {
        subtitle_timeout_timer_ = lv_timer_create([](lv_timer_t* timer) {
            auto* self = static_cast<LcdDisplay*>(lv_timer_get_user_data(timer));
            lv_timer_pause(timer);
            if (!self->subtitle_timeout_active_) return;
            self->subtitle_timeout_active_ = false;
            if (self->chat_message_label_ != nullptr) {
                lv_label_set_text(self->chat_message_label_, "");
            }
            if (self->bottom_bar_ != nullptr) {
                lv_obj_add_flag(self->bottom_bar_, LV_OBJ_FLAG_HIDDEN);
            }
        }, 8000, this);
    } else {
        lv_timer_set_period(subtitle_timeout_timer_, 8000);
        lv_timer_reset(subtitle_timeout_timer_);
        lv_timer_resume(subtitle_timeout_timer_);
    }
    if (subtitle_timeout_timer_ == nullptr) {
        subtitle_timeout_active_ = false;
        ESP_LOGW(TAG, "Unable to allocate subtitle timeout timer");
    }
}
'''

FACE_METHOD = r'''bool SetAvatarExpressionLocked(const char* face) {
        const int idx = FaceNameToIndex(face);
        if (idx < 0) return false;
        // QIANMO_DISPLAY_TIMING_V1: each successfully displayed non-idle face
        // gets a fresh five-second hold. Blink frames do not reset this timer.
        if (idx != 0 && avatar_face_timeout_timer_ == nullptr) {
            avatar_face_timeout_timer_ = lv_timer_create([](lv_timer_t* timer) {
                auto* self = static_cast<StackChanBoard*>(lv_timer_get_user_data(timer));
                if (self->current_avatar_face_ == "off" ||
                    self->current_avatar_face_ == "idle") {
                    lv_timer_pause(timer);
                    return;
                }
                if (self->avatar_fetch_in_progress_.load(std::memory_order_acquire)) {
                    // Do not read the avatar set while its storage is changing.
                    lv_timer_set_period(timer, 100);
                    lv_timer_reset(timer);
                    return;
                }
                if (!self->SetAvatarExpressionLocked("idle")) {
                    // A temporarily unavailable screen must not leave the old
                    // expression latched permanently.
                    lv_timer_set_period(timer, 100);
                    lv_timer_reset(timer);
                }
            }, 5000, this);
            if (avatar_face_timeout_timer_ == nullptr) return false;
            lv_timer_pause(avatar_face_timeout_timer_);
        }
        current_face_index_ = idx;
        active_layer_ = ActiveLayer::FACE;
        if (!RenderAvatarLocked()) return false;
        current_avatar_face_ = face;
        if (avatar_face_timeout_timer_ != nullptr) {
            if (idx == 0) {
                lv_timer_pause(avatar_face_timeout_timer_);
            } else {
                lv_timer_set_period(avatar_face_timeout_timer_, 5000);
                lv_timer_reset(avatar_face_timeout_timer_);
                lv_timer_resume(avatar_face_timeout_timer_);
            }
        }
        return true;
    }'''

def patched_sources(sources):
    h, cc, board = (sources[n] for n in ("main/display/lcd_display.h",
                        "main/display/lcd_display.cc", "main/boards/stackchan/stackchan.cc"))
    if any(MARKER in s for s in sources.values()):
        raise ValueError("This fix is already present, or only partly applied; do not apply twice")
    h = replace_once(h, "    bool hide_subtitle_ = false;",
        "    // QIANMO_DISPLAY_TIMING_V1: lifetime independent of avatar changes.\n"
        "    lv_timer_t* subtitle_timeout_timer_ = nullptr;\n"
        "    bool subtitle_timeout_active_ = false;\n"
        "    void ArmSubtitleTimeoutLocked();\n"
        "    bool hide_subtitle_ = false;")
    h = replace_once(h, "    void SetHideSubtitle(bool hide);",
        "    void SetHideSubtitle(bool hide);\n"
        "    // Caller must already hold the display lock; does not change visibility.\n"
        "    void RestoreStackChanOverlayOrderLocked();")

    cc = replace_once(cc, "LcdDisplay::~LcdDisplay() {\n",
        "LcdDisplay::~LcdDisplay() {\n"
        "    {\n"
        "        DisplayLockGuard lock(this);\n"
        "        if (subtitle_timeout_timer_ != nullptr) {\n"
        "            lv_timer_delete(subtitle_timeout_timer_);\n"
        "            subtitle_timeout_timer_ = nullptr;\n"
        "        }\n"
        "        subtitle_timeout_active_ = false;\n"
        "    }\n")
    def chat(fn):
        fn = replace_once(fn, "    lv_label_set_text(chat_message_label_, content);",
r'''#if CONFIG_BOARD_TYPE_STACKCHAN
    // Empty status/state messages must not cut a timed subtitle short.
    if (subtitle_timeout_active_ && (content == nullptr || content[0] == '\0')) {
        return;
    }
    if (subtitle_timeout_timer_ != nullptr) lv_timer_pause(subtitle_timeout_timer_);
    subtitle_timeout_active_ = role != nullptr && strcmp(role, "assistant") == 0 &&
                               content != nullptr && content[0] != '\0';
    if (subtitle_timeout_active_) ArmSubtitleTimeoutLocked();
#endif
    lv_label_set_text(chat_message_label_, content == nullptr ? "" : content);''')
        return fn[:-1] + "    RestoreStackChanOverlayOrderLocked();\n}"
    cc = modify_function(cc, "void LcdDisplay::SetChatMessage(", chat)
    def clear(fn):
        return replace_once(fn, "    DisplayLockGuard lock(this);",
            "    DisplayLockGuard lock(this);\n"
            "#if CONFIG_BOARD_TYPE_STACKCHAN\n"
            "    if (subtitle_timeout_active_) return;\n"
            "#endif")
    cc = modify_function(cc, "void LcdDisplay::ClearChatMessages(", clear)
    def preview(fn):
        return replace_once(fn,
            "    lv_obj_remove_flag(preview_image_, LV_OBJ_FLAG_HIDDEN);",
            "    lv_obj_remove_flag(preview_image_, LV_OBJ_FLAG_HIDDEN);\n"
            "    RestoreStackChanOverlayOrderLocked();")
    cc = modify_function(cc, "void LcdDisplay::SetPreviewImage(", preview)
    def hide(fn):
        return fn[:-1] + "    RestoreStackChanOverlayOrderLocked();\n}"
    cc = modify_function(cc, "void LcdDisplay::SetHideSubtitle(", hide)
    cc += "\n" + OVERLAY_FUNCTIONS

    board = replace_once(board, '    std::string current_avatar_face_ = "idle";',
        '    std::string current_avatar_face_ = "idle";\n'
        '    lv_timer_t* avatar_face_timeout_timer_ = nullptr;')
    board = modify_function(board, "    bool SetAvatarExpressionLocked(",
        lambda fn: "    " + FACE_METHOD)
    def render(fn):
        return replace_once(fn,
            "        BringListeningIndicatorToFrontLocked();",
            "        BringListeningIndicatorToFrontLocked();\n"
            "        display_->RestoreStackChanOverlayOrderLocked();")
    board = modify_function(board, "    bool RenderAvatarLocked(", render)
    def off(fn):
        return replace_once(fn,
            '            if (avatar_img_ != nullptr) {\n'
            '                lv_obj_add_flag(avatar_img_, LV_OBJ_FLAG_HIDDEN);\n'
            '            }\n'
            '        }\n'
            '        current_avatar_face_ = "off";',
            '            if (avatar_face_timeout_timer_ != nullptr) {\n'
            '                lv_timer_pause(avatar_face_timeout_timer_);\n'
            '            }\n'
            '            if (avatar_img_ != nullptr) {\n'
            '                lv_obj_add_flag(avatar_img_, LV_OBJ_FLAG_HIDDEN);\n'
            '            }\n'
            '            current_avatar_face_ = "off";\n'
            '        }')
    board = modify_function(board, "    bool SetAvatarOff(", off)
    # Touch faces use the same minimum five-second timer. The old independent
    # three-second timer would otherwise revert a newer MCP face prematurely.
    for signature in ["    void HandleTap(", "    void HandleStroke("]:
        board = modify_function(board, signature,
            lambda fn: replace_once(fn, "        ScheduleIdleRevert();\n", ""))
    return {"main/display/lcd_display.h": h,
            "main/display/lcd_display.cc": cc,
            "main/boards/stackchan/stackchan.cc": board}

FILES = ("main/display/lcd_display.h", "main/display/lcd_display.cc",
         "main/boards/stackchan/stackchan.cc")

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path,
                   default=Path.home() / "stackchan-subtitle-build/firmware")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    source = args.source.resolve()
    if not (source / "CMakeLists.txt").is_file():
        raise SystemExit("Firmware source not found: " + str(source))
    if 'set(PROJECT_VER "2.2.6")' not in (source / "CMakeLists.txt").read_text(encoding="utf-8-sig"):
        raise SystemExit("Unexpected firmware version; no files changed")
    config = source / "sdkconfig"
    if config.is_file() and "CONFIG_USE_WECHAT_MESSAGE_STYLE=y" in config.read_text(encoding="utf-8-sig"):
        raise SystemExit("Wechat chat UI mode is unsupported by this patch; no files changed")
    art = [source/"main/boards/stackchan/avatar_images.local.cc",
           source/"main/boards/stackchan/avatar_images.local.h"]
    if not all(f.is_file() for f in art):
        raise SystemExit("Local avatar art is missing; stop before changing the personal build")
    artwork_hashes = {str(f.relative_to(source)): digest(f) for f in art}
    originals = {n: (source/n).read_bytes() for n in FILES}
    texts = {n: b.decode("utf-8-sig").replace("\r\n", "\n")
             for n, b in originals.items()}
    updated = patched_sources(texts)  # Validate all anchors before writing anything.
    if args.dry_run:
        print("CHECK PASSED: three source files match; no files changed.")
        return
    backup = Path.home()/"stackchan-display-backup"/datetime.now().strftime("%Y%m%d-%H%M%S")
    backup.mkdir(parents=True, exist_ok=False)
    for n, b in originals.items():
        target = backup/n
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b)
    metadata = {"source": str(source), "originals": {n: hashlib.sha256(b).hexdigest()
                for n, b in originals.items()}, "avatar": artwork_hashes}
    (backup/"backup.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    try:
        for n, text in updated.items():
            (source/n).write_text(text, encoding="utf-8", newline="\n")
        assert all(digest(source/n) == h for n, h in artwork_hashes.items())
    except BaseException:
        for n, b in originals.items(): (source/n).write_bytes(b)
        raise
    print("PATCHED:", source)
    print("BACKUP:", backup)
    print("Face hold: 5 seconds; assistant subtitles: 8 seconds.")
    print("Avatar frames were preserved. Nothing was compiled, flashed or restarted.")

if __name__ == "__main__":
    main()

