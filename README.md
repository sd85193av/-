# 手勢上下滾動控制器

這是一個 Windows 手勢控制原型，使用筆電攝影機與 MediaPipe 在本機追蹤手部關節，透過「食指＋中指」的上下移動控制畫面滾動。

攝影機影像只在本機即時處理，不會上傳或儲存。

## 目前啟用的手勢

僅保留兩指上下滾動：

- 食指＋中指往上移動：畫面往上滾動。
- 食指＋中指往下移動：畫面往下滾動。
- 一次兩指手勢會鎖定第一次判定的方向。
- 手移回起點的反方向動作不會觸發滾動。
- 若要切換方向，短暫收起中指，再重新伸出食指＋中指。

游標移動、握拳點擊、拖曳、右鍵、上一頁與下一頁目前全部停用。

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
- 放開兩指後可以切換方向。
- 其他點擊、拖曳、翻頁與游標功能在 scroll-only 模式下停用。
- 設定載入、手部幾何判定與監測面板繪製。

## 主要設定

設定檔位於 `config.json`：

- `gestures.scroll_only`：只允許上下滾動。
- `gestures.scroll_direction_lock_until_release`：鎖定方向直到放開兩指。
- `gestures.scroll_step_distance`：每次觸發所需的手部位移。
- `gestures.scroll_wheel_delta`：基礎滾動量。
- `gestures.scroll_max_wheel_delta`：快速移動時的最大滾動量。
- `display.detail_follow_window_title`：監測視窗要跟隨的視窗標題。

