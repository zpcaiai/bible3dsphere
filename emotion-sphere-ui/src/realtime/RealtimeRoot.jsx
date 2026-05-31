// 全局实时根组件：在 App 顶层挂载一次。负责
//   1) 用单例 store 维持唯一的 WebSocket 连接（按登录状态启停）
//   2) 渲染**全局来电弹窗 + 通话面板**——无论用户在哪个页面都能接到来电。
import { useEffect } from 'react'
import realtimeStore from './realtimeStore'
import { useRealtimeState } from './useRealtimeStore'
import LiveKitCall from './LiveKitCall'

export default function RealtimeRoot({ user }) {
  useEffect(() => {
    realtimeStore.start(user)
    return () => { /* keep connection across page switches; stop only when user clears */ }
  }, [user])

  // when user logs out, tear down
  useEffect(() => {
    if (!user) realtimeStore.stop()
  }, [user])

  const { incomingCall, activeCall } = useRealtimeState()

  if (!user) return null

  return (
    <>
      {activeCall && (
        <LiveKitCall
          url={activeCall.creds.url}
          token={activeCall.creds.token}
          title={activeCall.title}
          selfName={realtimeStore.selfName()}
          outgoing={activeCall.outgoing}
          onLeave={() => realtimeStore.endCall()}
        />
      )}

      {incomingCall && !activeCall && (
        <div className="communion-invite-overlay">
          <div className="communion-invite glass">
            <div className="communion-invite-title">📞 {incomingCall.name} 邀请你语音通话</div>
            <div className="communion-invite-actions">
              <button className="communion-accept" onClick={() => realtimeStore.acceptIncoming()}>接听</button>
              <button className="communion-decline" onClick={() => realtimeStore.declineIncoming()}>拒绝</button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
