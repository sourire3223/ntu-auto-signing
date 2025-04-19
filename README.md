# ntu-auto-signing (台大到勤自動帳號簽到退)

利用爬蟲方式，完成登入計中帳號、進入到勤差假系統、簽到/簽退一連串的流程。配合排程系統設定好需要打卡的時間，程式就能夠自動替你完成打卡。

省去人手打卡所花費的時間及避免忘記打卡所帶來的問題。

## Requirements (Python 3.13+)
透過 uv 下載套件 
```bash
uv sync
```

如果不想使用 uv 下載套件，可以直接透過 pip 安裝依賴套件。請注意，`requirements.txt` 是由 `uv pip compile` 產生的，務必確保 `requirements.txt` 與 `uv.lock` 版本一致，以避免可能的相容性問題。
```bash
pip install -r requirements.txt
```

## Quick Start
修改 `config.ini` 檔案設定，`[MAIL]` 用於設定 email 通知，將 `from` 改為發送通知的 gmail 帳號，`password` 為對應的應用程式密碼，`to` 為接收通知的 email 地址。`[USER]` 為 MyNTU 帳號資料，將 `username` 及 `password` 改為自己的帳號密碼。

### 執行方式
程式提供多種執行模式，可以透過命令列參數控制：

```bash
# 單次簽到
python -m src.main signin

# 單次簽退
python -m src.main signout

# 檢查目前簽到狀態，在0~17內確認簽到，17~24確認簽退
python -m src.main check

# 持續執行模式，會自動排程簽到簽退
python -m src.main loop
```
您也可以指定設定檔的路徑：
```bash
python -m src.main signin -c /path/to/config.ini
```

### Docker 執行方式

除了直接使用 Python 執行外，本專案也支援 Docker 容器化部署，提供更一致的執行環境：

```bash
# 建立 Docker 映像檔
docker build -t ntu-auto-signing .

# 執行簽到
docker run --rm -v $(pwd)/config.ini:/app/config.ini ntu-auto-signing signin

# 執行簽退
docker run --rm -v $(pwd)/config.ini:/app/config.ini ntu-auto-signing signout

# 檢查狀態
docker run --rm -v $(pwd)/config.ini:/app/config.ini ntu-auto-signing check

# 持續執行模式（自動重啟）
docker run -d --restart=always --name ntu-auto-signing -v $(pwd)/config.ini:/app/config.ini ntu-auto-signing loop
```
請注意，若 windows 自動更新，可能會導致 docker 沒有正常在開機時啟動，導致自動重啟失敗。
