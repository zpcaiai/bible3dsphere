import { useState } from 'react'
import { loginWithEmail, registerWithEmail, sendEmailCode } from './auth'

const cardStyle = {
  width: '100%',
  maxWidth: '360px',
  background: 'rgba(28,28,30,0.92)',
  border: '0.5px solid rgba(255,255,255,0.08)',
  backdropFilter: 'blur(20px) saturate(180%)',
  WebkitBackdropFilter: 'blur(20px) saturate(180%)',
  borderRadius: '20px',
  padding: '28px 24px',
  boxSizing: 'border-box',
}

const inputStyle = {
  width: '100%',
  minHeight: '48px',
  background: 'rgba(120,120,128,0.18)',
  border: '0.5px solid rgba(255,255,255,0.1)',
  borderRadius: '12px',
  color: '#fff',
  fontSize: '16px',
  padding: '12px 14px',
  boxSizing: 'border-box',
  outline: 'none',
  fontFamily: 'inherit',
  WebkitAppearance: 'none',
}

const primaryBtnStyle = (disabled) => ({
  width: '100%',
  minHeight: '50px',
  border: 'none',
  borderRadius: '12px',
  background: '#007aff',
  color: '#fff',
  fontSize: '17px',
  fontWeight: 600,
  cursor: disabled ? 'not-allowed' : 'pointer',
  opacity: disabled ? 0.5 : 1,
  transition: 'opacity 0.15s',
  fontFamily: 'inherit',
})

const mutedText = { fontSize: '12px', color: 'rgba(255,255,255,0.35)', textAlign: 'center', lineHeight: 1.6, margin: '16px 0 0' }
const errorText = { fontSize: '13px', color: '#ff3b30', margin: '10px 0 0', textAlign: 'center' }
const labelStyle = { fontSize: '13px', color: 'rgba(255,255,255,0.5)', marginBottom: '6px', display: 'block' }

export default function LoginScreen({ onLogin, onBack }) {
  const [tab, setTab] = useState('login') // 'login' | 'register'
  return (
    <div style={{
      width: '100%', height: '100dvh', background: '#000',
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'center', padding: '24px 20px', boxSizing: 'border-box',
      position: 'relative',
    }}>
      {onBack && (
        <button
          onClick={onBack}
          style={{
            position: 'absolute', top: '16px', left: '16px',
            background: 'rgba(120,120,128,0.2)', border: 'none',
            borderRadius: '50%', width: '36px', height: '36px',
            color: 'rgba(255,255,255,0.7)', fontSize: '18px',
            cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontFamily: 'inherit',
          }}
        >‹</button>
      )}
      <div style={{ textAlign: 'center', marginBottom: '32px' }}>
        <div style={{ fontSize: '64px', lineHeight: 1, marginBottom: '12px' }}>🔮</div>
        <h1 style={{ margin: 0, fontSize: '26px', fontWeight: 700, color: '#fff', letterSpacing: '-0.02em' }}>情感星球</h1>
        <p style={{ margin: '6px 0 0', fontSize: '14px', color: 'rgba(255,255,255,0.4)' }}>Bible Emotion Sphere</p>
      </div>

      <div style={cardStyle}>
        {/* Tab 切换 */}
        <div style={{
          display: 'flex', gap: '2px', padding: '3px',
          background: 'rgba(120,120,128,0.2)', borderRadius: '10px', marginBottom: '24px',
        }}>
          {[['login', '登录'], ['register', '注册']].map(([key, label]) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              style={{
                flex: 1, minHeight: '36px', border: 'none', borderRadius: '8px', fontFamily: 'inherit',
                fontSize: '14px', fontWeight: 500, cursor: 'pointer',
                background: tab === key ? '#007aff' : 'transparent',
                color: tab === key ? '#fff' : 'rgba(255,255,255,0.5)',
                transition: 'background 0.2s, color 0.2s',
              }}
            >{label}</button>
          ))}
        </div>

        {tab === 'login'
          ? <LoginForm onLogin={onLogin} />
          : <RegisterForm onDone={() => setTab('login')} onLogin={onLogin} />
        }

        <p style={mutedText}>登录即表示同意服务条款与隐私政策</p>
      </div>
    </div>
  )
}

function LoginForm({ onLogin }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const data = await loginWithEmail(email.trim(), password)
      if (data.user && onLogin) onLogin(data.user)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
      <div>
        <label style={labelStyle}>邮箱</label>
        <input
          type="email" required value={email} onChange={e => setEmail(e.target.value)}
          placeholder="you@example.com" autoComplete="email"
          style={inputStyle}
        />
      </div>
      <div>
        <label style={labelStyle}>密码</label>
        <input
          type="password" required value={password} onChange={e => setPassword(e.target.value)}
          placeholder="输入密码" autoComplete="current-password"
          style={inputStyle}
        />
      </div>
      {error && <p style={errorText}>{error}</p>}
      <button type="submit" disabled={loading} style={primaryBtnStyle(loading)}>
        {loading ? '登录中...' : '登录'}
      </button>
    </form>
  )
}

function RegisterForm({ onDone, onLogin }) {
  const [email, setEmail] = useState('')
  const [code, setCode] = useState('')
  const [password, setPassword] = useState('')
  const [nickname, setNickname] = useState('')
  const [sendLoading, setSendLoading] = useState(false)
  const [regLoading, setRegLoading] = useState(false)
  const [codeSent, setCodeSent] = useState(false)
  const [countdown, setCountdown] = useState(0)
  const [error, setError] = useState('')

  const handleEmailChange = (nextEmail) => {
    setEmail(nextEmail)
    if (codeSent) {
      setCodeSent(false)
      setCode('')
    }
  }

  const startCountdown = () => {
    setCountdown(60)
    const t = setInterval(() => {
      setCountdown(c => { if (c <= 1) { clearInterval(t); return 0 } return c - 1 })
    }, 1000)
  }

  const handleSendCode = async () => {
    setError('')
    setSendLoading(true)
    try {
      await sendEmailCode(email.trim())
      setCodeSent(true)
      startCountdown()
    } catch (err) {
      setError(err.message)
    } finally {
      setSendLoading(false)
    }
  }

  const handleRegister = async (e) => {
    e.preventDefault()
    setError('')
    setRegLoading(true)
    try {
      const data = await registerWithEmail(email.trim(), code.trim(), password, nickname.trim())
      if (data.user && onLogin) onLogin(data.user)
    } catch (err) {
      setError(err.message)
    } finally {
      setRegLoading(false)
    }
  }

  return (
    <form onSubmit={handleRegister} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
      <div>
        <label style={labelStyle}>邮箱</label>
        <div style={{ display: 'flex', gap: '8px' }}>
          <input
            type="email" required value={email} onChange={e => handleEmailChange(e.target.value)}
            placeholder="you@example.com" autoComplete="email"
            style={{ ...inputStyle, flex: 1 }}
          />
          <button
            type="button"
            onClick={handleSendCode}
            disabled={sendLoading || countdown > 0 || !email.includes('@')}
            style={{
              flexShrink: 0, minHeight: '48px', padding: '0 14px', border: 'none',
              borderRadius: '12px', fontSize: '13px', fontWeight: 500, fontFamily: 'inherit',
              background: 'rgba(0,122,255,0.2)', color: '#007aff', cursor: 'pointer',
              opacity: (sendLoading || countdown > 0 || !email.includes('@')) ? 0.5 : 1,
              whiteSpace: 'nowrap',
            }}
          >
            {countdown > 0 ? `${countdown}s` : sendLoading ? '发送中' : '获取验证码'}
          </button>
        </div>
      </div>
      <div>
        <label style={labelStyle}>验证码</label>
        <input
          type="text" required value={code} onChange={e => setCode(e.target.value)}
          placeholder="6位验证码" maxLength={6} inputMode="numeric"
          style={inputStyle}
        />
      </div>
      <div>
        <label style={labelStyle}>密码（至少6位）</label>
        <input
          type="password" required value={password} onChange={e => setPassword(e.target.value)}
          placeholder="设置登录密码" autoComplete="new-password" minLength={6}
          style={inputStyle}
        />
      </div>
      <div>
        <label style={labelStyle}>昵称（选填）</label>
        <input
          type="text" value={nickname} onChange={e => setNickname(e.target.value)}
          placeholder="你的名字"
          style={inputStyle}
        />
      </div>
      {error && <p style={errorText}>{error}</p>}
      <button type="submit" disabled={regLoading || !codeSent} style={primaryBtnStyle(regLoading || !codeSent)}>
        {regLoading ? '注册中...' : '注册并登录'}
      </button>
    </form>
  )
}

