# (已废弃) 自建 coturn

语音通话改用现有的 **LiveKit SFU** 方案（见 `VoiceRoomPage.jsx` +
`backend/routers/voice.py`），LiveKit 自带 TURN，**无需自建 coturn**。
本文件保留为空壳仅因沙盒 FUSE 挂载不允许删除文件，正常检出可删除。

LiveKit 所需环境变量见 `.env.example` 的 `LIVEKIT_*` 段与 `voice.py` 顶部说明。
