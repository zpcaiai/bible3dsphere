import { useState } from 'react'
import { loginWithEmail, registerWithEmail, sendEmailCode, sendResetCode, resetPassword } from './auth'

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

export default function LoginScreen({ onLogin, onBack, message }) {
  const [tab, setTab] = useState('login') // 'login' | 'register' | 'reset'
  const [sharedEmail, setSharedEmail] = useState('') // Shared email across tabs
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
        {/* 提示信息 */}
        {message && (
          <div style={{
            background: 'rgba(0,122,255,0.15)',
            border: '1px solid rgba(0,122,255,0.3)',
            borderRadius: '10px',
            padding: '12px 16px',
            marginBottom: '16px',
            fontSize: '13px',
            color: 'rgba(255,255,255,0.9)',
            textAlign: 'center',
            lineHeight: '1.5',
          }}>
            {message}
          </div>
        )}
        {/* Tab 切换 */}
        <div style={{
          display: 'flex', gap: '2px', padding: '3px',
          background: 'rgba(120,120,128,0.2)', borderRadius: '10px', marginBottom: '24px',
        }}>
          {[['login', '登录'], ['register', '注册'], ['reset', '重置密码']].map(([key, label]) => (
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

        {tab === 'login' && <LoginForm email={sharedEmail} setEmail={setSharedEmail} onLogin={onLogin} onReset={() => setTab('reset')} />}
        {tab === 'register' && <RegisterForm email={sharedEmail} setEmail={setSharedEmail} onDone={() => setTab('login')} onLogin={onLogin} />}
        {tab === 'reset' && <ResetPasswordForm email={sharedEmail} setEmail={setSharedEmail} onDone={() => setTab('login')} />}

        <p style={mutedText}>登录即表示同意服务条款与隐私政策</p>
      </div>
    </div>
  )
}

function LoginForm({ email, setEmail, onLogin, onReset }) {
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
      <div style={{ textAlign: 'center', marginTop: '8px' }}>
        <button
          type="button"
          onClick={onReset}
          style={{
            background: 'none', border: 'none', padding: 0,
            fontSize: '13px', color: 'rgba(0,122,255,0.8)', cursor: 'pointer',
            fontFamily: 'inherit',
          }}
        >
          忘记密码？
        </button>
      </div>
    </form>
  )
}

function RegisterForm({ email, setEmail, onDone, onLogin }) {
  const [code, setCode] = useState('')
  const [password, setPassword] = useState('')
  const [nickname, setNickname] = useState('')
  const [sendLoading, setSendLoading] = useState(false)
  const [regLoading, setRegLoading] = useState(false)
  const [codeSent, setCodeSent] = useState(false)
  const [countdown, setCountdown] = useState(0)
  const [error, setError] = useState('')
  const [devCode, setDevCode] = useState('')  // shown when SMTP is not configured

  const handleEmailChange = (nextEmail) => {
    setEmail(nextEmail)
    if (codeSent) {
      setCodeSent(false)
      setCode('')
      setDevCode('')
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
    setDevCode('')
    setSendLoading(true)
    try {
      const data = await sendEmailCode(email.trim())
      // Check if email already registered
      if (data.registered) {
        setError(data.message || '该邮箱已注册，请直接登录')
        setSendLoading(false)
        // Auto switch to login tab after 1.5s
        setTimeout(() => onDone && onDone(), 1500)
        return
      }
      setCodeSent(true)
      startCountdown()
      if (data.dev_code) {
        setDevCode(data.dev_code)
      }
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
        {devCode && (
          <p style={{ fontSize: '12px', color: '#34c759', margin: '6px 0 0', textAlign: 'center' }}>
            开发模式 — 验证码: <b>{devCode}</b>（请在上方输入）
          </p>
        )}
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

function ResetPasswordForm({ email, setEmail, onDone }) {
  const [code, setCode] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [sendLoading, setSendLoading] = useState(false)
  const [resetLoading, setResetLoading] = useState(false)
  const [codeSent, setCodeSent] = useState(false)
  const [countdown, setCountdown] = useState(0)
  const [error, setError] = useState('')
  const [devCode, setDevCode] = useState('')
  const [success, setSuccess] = useState(false)

  const startCountdown = () => {
    setCountdown(60)
    const t = setInterval(() => {
      setCountdown(c => { if (c <= 1) { clearInterval(t); return 0 } return c - 1 })
    }, 1000)
  }

  const handleSendCode = async () => {
    setError('')
    setDevCode('')
    setSendLoading(true)
    try {
      const data = await sendResetCode(email.trim())
      setCodeSent(true)
      startCountdown()
      if (data.dev_code) {
        setDevCode(data.dev_code)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setSendLoading(false)
    }
  }

  const handleReset = async (e) => {
    e.preventDefault()
    setError('')

    if (password !== confirmPassword) {
      setError('两次输入的密码不一致')
      return
    }
    if (password.length < 6) {
      setError('密码至少需要6位')
      return
    }

    setResetLoading(true)
    try {
      await resetPassword(email.trim(), code.trim(), password)
      setSuccess(true)
      setTimeout(() => onDone && onDone(), 2000)
    } catch (err) {
      setError(err.message)
    } finally {
      setResetLoading(false)
    }
  }

  if (success) {
    return (
      <div style={{ textAlign: 'center', padding: '20px' }}>
        <div style={{ fontSize: '48px', marginBottom: '16px' }}>✅</div>
        <div style={{ fontSize: '16px', color: '#fff', marginBottom: '8px' }}>密码重置成功</div>
        <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.5)' }}>请使用新密码登录</div>
      </div>
    )
  }

  return (
    <form onSubmit={handleReset} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
      <div>
        <label style={labelStyle}>注册邮箱</label>
        <div style={{ display: 'flex', gap: '8px' }}>
          <input
            type="email" required value={email} onChange={e => setEmail(e.target.value)}
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
        {devCode && (
          <p style={{ fontSize: '12px', color: '#34c759', margin: '6px 0 0', textAlign: 'center' }}>
            开发模式 — 验证码: <b>{devCode}</b>（请在上方输入）
          </p>
        )}
      </div>
      <div>
        <label style={labelStyle}>新密码（至少6位）</label>
        <input
          type="password" required value={password} onChange={e => setPassword(e.target.value)}
          placeholder="设置新密码" autoComplete="new-password" minLength={6}
          style={inputStyle}
        />
      </div>
      <div>
        <label style={labelStyle}>确认密码</label>
        <input
          type="password" required value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)}
          placeholder="再次输入新密码" autoComplete="new-password"
          style={inputStyle}
        />
      </div>
      {error && <p style={errorText}>{error}</p>}
      <button type="submit" disabled={resetLoading || !codeSent} style={primaryBtnStyle(resetLoading || !codeSent)}>
        {resetLoading ? '重置中...' : '重置密码'}
      </button>
      <div style={{ textAlign: 'center', marginTop: '4px' }}>
        <button
          type="button"
          onClick={onDone}
          style={{
            background: 'none', border: 'none', padding: 0,
            fontSize: '13px', color: 'rgba(255,255,255,0.4)', cursor: 'pointer',
            fontFamily: 'inherit',
          }}
        >
          返回登录
        </button>
      </div>
    </form>
  )
}

