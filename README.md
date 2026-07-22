# 手勢上下滾動與游標控制器

這是一個 Windows 手勢控制原型，使用筆電攝影機與 MediaPipe 在本機追蹤手部關節。單獨伸出食指可移動鼠標、拇指向外張開可左鍵單擊，伸出食指＋中指可控制畫面上下滾動。

攝影機影像只在本機即時處理，不會上傳或儲存。

## 目前啟用的手勢

目前只保留游標移動與兩指上下滾動：

- 單獨伸出食指：鼠標跟隨食指位置移動，不會點擊。
- 維持單食指姿勢並將拇指向外張開：左鍵單擊一次。
- 拇指持續張開不會連點；收回後再次張開才可再點。
- 食指＋中指往上移動：畫面往上滾動。
- 食指＋中指往下移動：畫面往下滾動。
- 短促的反方向動作會視為回手，不會觸發反向滾動。
- 反方向持續達到時間與距離門檻後會自動切換方向，不必收起手指。

握拳點擊、拖曳、右鍵、上一頁與下一頁目前全部停用。

## 監測視窗

程式包含：

- `Gesture Mouse - Camera Angle`：攝影機預覽畫面。
- `Gesture Mouse - Tracking Details`：手部關節、模式、FPS 與動作狀態。

追蹤細節視窗會尋找標題為 `ChatGPT` 的 Codex 視窗，並自動移到 Codex 所在螢幕的右側；若找不到 Codex，才使用 `config.json` 的 `display.detail_monitor_index`。

## 安裝

雙擊：

```text
安裝或修復環境.bat
```

安裝程式會：

1. 建立 `.venv`。
2. 安裝 `requirements.txt` 中的套件。
3. 在模型不存在時下載 MediaPipe 手部辨識模型。

## 執行

一般執行：

```text
啟動手勢滑鼠.bat
```

不控制畫面的安全測試：

```text
安全測試_不控制滑鼠.bat
```

快捷鍵：

- `F8`：暫停或恢復控制。
- `F9`：顯示或隱藏追蹤細節。
- `Esc`：結束程式。

## 測試

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

目前測試涵蓋：

- 兩指上下滾動。
- 上下回手動作不會反向觸發。
- 持續反向移動可在不收手指的情況下切換方向。
- 單食指只移動游標，不會產生點擊事件。
- 單食指＋拇指外張只會產生一次左鍵點擊。
- 兩指滾動時拇指外張不會誤觸點擊。
- 其他點擊、拖曳與翻頁功能在 scroll-only 模式下停用。
- 設定載入、手部幾何判定與監測面板繪製。

## 主要設定

設定檔位於 `config.json`：

- `gestures.scroll_only`：停用點擊、拖曳與翻頁手勢。
- `gestures.pointer_enabled`：允許單食指移動游標。
- `gestures.thumb_click_enabled`：允許拇指外張左鍵單擊。
- `gestures.thumb_click_open_threshold`：拇指外張的啟動門檻。
- `gestures.thumb_click_release_threshold`：拇指收回的解除門檻。
- `gestures.thumb_click_hold_seconds`：單擊前需穩定張開的時間。
- `gestures.scroll_return_motion_suppression`：抑制短促的反向回手動作。
- `gestures.scroll_direction_switch_seconds`：自動切換方向所需的持續時間。
- `gestures.scroll_direction_switch_distance`：自動切換方向所需的反向位移。
- `gestures.scroll_step_distance`：每次觸發所需的手部位移。
- `gestures.scroll_down_activation_distance`：向下開始滾動所需的位移。
- `gestures.scroll_down_step_distance`：向下連續觸發的步進距離。
- `gestures.scroll_down_wheel_multiplier`：向下滾動量補償倍率。
- `gestures.scroll_wheel_delta`：基礎滾動量。
- `gestures.scroll_max_wheel_delta`：以 30 FPS 為基準的單幀最大滾動量。
- `gestures.scroll_output_smoothing`：滾動輸出速度的平滑比例。
- `gestures.scroll_idle_reset_seconds`：追蹤中斷或停頓後重新對齊的時間。
- `display.detail_follow_window_title`：監測視窗要跟隨的視窗標題。
