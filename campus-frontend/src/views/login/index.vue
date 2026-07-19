<template>
  <main class="login-page">
    <section class="login-brand">
      <div class="brand-overlay" />
      <img class="brand-campus" src="/assets/xikang-campus-05.jpg" alt="河海大学西康路校区" />
      <div class="brand-water" />
      <div class="brand-copy">
        <div class="login-wordmark">
          <div class="university-wordmark">
            <img src="/assets/hhu-emblem.jpg" alt="河海大学校徽" />
            <div><strong>河海大学</strong><span>HOHAI UNIVERSITY</span></div>
          </div>
          <i />
          <div class="platform-wordmark"><strong>河海智问</strong><span>校园知识智能问答平台</span></div>
        </div>
        <div class="brand-slogan"><span /><p>校园知识，可信赖，可追溯</p><span /></div>
      </div>
      <div class="brand-points">
        <article><el-icon><Collection /></el-icon><div><strong>校园知识</strong><span>汇聚河海权威知识资源<br />覆盖教学、科研与管理</span></div></article>
        <article><el-icon><DocumentChecked /></el-icon><div><strong>可信引用</strong><span>来源权威，引用规范<br />知识可信，过程可追溯</span></div></article>
        <article><el-icon><Search /></el-icon><div><strong>智能检索</strong><span>语义理解，精准匹配<br />智能问答，高效获取</span></div></article>
      </div>
    </section>

    <section class="login-panel">
      <div class="login-card">
        <div class="mobile-logo"><AppLogo /></div>
        <div class="login-tabs">
          <button :class="{ active: !isRegister }" type="button" @click="switchMode(false)">登录</button>
          <button :class="{ active: isRegister }" type="button" @click="switchMode(true)">注册</button>
        </div>

        <transition name="form-fade" mode="out-in">
          <div v-if="!isRegister" key="login">
            <el-form ref="formRef" :model="form" :rules="rules" size="large" label-position="top" @keyup.enter="handleLogin">
              <el-form-item label="用户名" prop="username"><el-input v-model="form.username" placeholder="请输入用户名" :prefix-icon="User" /></el-form-item>
              <el-form-item label="密码" prop="password"><el-input v-model="form.password" type="password" placeholder="请输入密码" show-password :prefix-icon="Lock" /></el-form-item>
              <el-form-item label="图形验证码" prop="code">
                <div class="captcha-row">
                  <el-input v-model="form.code" placeholder="请输入验证码" :prefix-icon="Key" />
                  <button class="captcha-button" type="button" title="点击刷新验证码" @click="refreshCaptcha"><img v-if="captchaImg" :src="captchaImg" alt="图形验证码" /><span v-else>8 3 K 7</span></button>
                  <button class="captcha-refresh" type="button" aria-label="刷新验证码" @click="refreshCaptcha"><el-icon><RefreshRight /></el-icon></button>
                </div>
              </el-form-item>
              <div class="login-options"><el-checkbox v-model="rememberMe">记住我</el-checkbox><button type="button" @click="showForgotTip">忘记密码？</button></div>
              <el-button class="submit-button" type="primary" :loading="loading" @click="handleLogin">登录</el-button>
              <button class="guest-entry" type="button" :disabled="loading" @click="handleGuestLogin">
                <el-icon><User /></el-icon> 访客进入 · 免注册直接体验问答
              </button>
            </el-form>
          </div>

          <div v-else key="register">
            <div class="form-title"><h2>创建账号</h2><p>填写基础信息，加入校园知识平台</p></div>
            <el-form ref="regRef" :model="regForm" :rules="regRules" size="large" label-position="top" @keyup.enter="handleRegister">
              <div class="form-grid">
                <el-form-item label="用户名" prop="username"><el-input v-model="regForm.username" placeholder="请输入用户名" /></el-form-item>
                <el-form-item label="昵称" prop="nickName"><el-input v-model="regForm.nickName" placeholder="请输入昵称" /></el-form-item>
                <el-form-item label="邮箱" prop="email"><el-input v-model="regForm.email" placeholder="请输入邮箱" /></el-form-item>
                <el-form-item label="手机号" prop="phone"><el-input v-model="regForm.phone" placeholder="请输入手机号" /></el-form-item>
              </div>
              <el-form-item label="密码" prop="password"><el-input v-model="regForm.password" type="password" placeholder="请输入密码" show-password /></el-form-item>
              <el-form-item label="确认密码" prop="confirmPwd"><el-input v-model="regForm.confirmPwd" type="password" placeholder="请再次输入密码" show-password /></el-form-item>
              <el-form-item label="图形验证码" prop="code"><div class="captcha-row"><el-input v-model="regForm.code" placeholder="请输入验证码" /><button class="captcha-button" type="button" @click="refreshCaptcha"><img :src="captchaImg" alt="图形验证码" /></button></div></el-form-item>
              <el-button class="submit-button" type="primary" :loading="loading" @click="handleRegister">注册</el-button>
            </el-form>
          </div>
        </transition>
        <p class="login-footnote">河海大学校园知识智能问答平台</p>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Collection, DocumentChecked, Key, Lock, RefreshRight, Search, User } from '@element-plus/icons-vue'
import { getCaptcha, register as registerApi } from '@/api/auth'
import { useUserStore } from '@/stores/user'
import AppLogo from '@/components/AppLogo.vue'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref()
const regRef = ref()
const loading = ref(false)
const isRegister = ref(false)
const rememberMe = ref(false)
const captchaImg = ref('')
const captchaUuid = ref('')

const form = reactive({ username: '', password: '', code: '' })
const regForm = reactive({ username: '', nickName: '', email: '', phone: '', password: '', confirmPwd: '', code: '' })
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  code: [{ required: true, message: '请输入验证码', trigger: 'blur' }],
}
const regRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  nickName: [{ required: true, message: '请输入昵称', trigger: 'blur' }],
  email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }],
  phone: [{ required: true, message: '请输入手机号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  confirmPwd: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: (_rule: unknown, value: string, callback: (error?: Error) => void) => value === regForm.password ? callback() : callback(new Error('两次密码不一致')), trigger: 'blur' },
  ],
  code: [{ required: true, message: '请输入验证码', trigger: 'blur' }],
}

async function refreshCaptcha() {
  try {
    const res = await getCaptcha()
    captchaUuid.value = res.data.uuid
    captchaImg.value = res.data.img
  } catch { captchaImg.value = '' }
}

function switchMode(register: boolean) {
  isRegister.value = register
  form.code = ''
  regForm.code = ''
  refreshCaptcha()
}

function showForgotTip() {
  ElMessage.info('请联系系统管理员重置密码')
}

async function handleLogin() {
  if (!(await formRef.value?.validate().catch(() => false))) return
  loading.value = true
  try {
    await userStore.login(form.username, form.password, captchaUuid.value, form.code)
    ElMessage.success('登录成功')
    await router.push('/home')
  } catch { await refreshCaptcha() } finally { loading.value = false }
}

async function handleGuestLogin() {
  loading.value = true
  try {
    await userStore.guestLogin()
    ElMessage.success('已进入访客模式，问答不会被保存')
    await router.push('/home')
  } catch { /* 拦截器已提示（如"访客通道已关闭"） */ } finally { loading.value = false }
}

async function handleRegister() {
  if (!(await regRef.value?.validate().catch(() => false))) return
  loading.value = true
  try {
    await registerApi({
      username: regForm.username,
      password: regForm.password,
      nickName: regForm.nickName,
      email: regForm.email,
      phone: regForm.phone,
      uuid: captchaUuid.value,
      code: regForm.code,
    })
    ElMessage.success('注册成功，请登录')
    form.username = regForm.username
    isRegister.value = false
    regForm.username = ''; regForm.nickName = ''; regForm.email = ''; regForm.phone = ''; regForm.password = ''; regForm.confirmPwd = ''; regForm.code = ''
    await refreshCaptcha()
  } catch { await refreshCaptcha() } finally { loading.value = false }
}

onMounted(refreshCaptcha)
</script>

<style scoped>
.login-page{display:grid;min-height:100vh;grid-template-columns:minmax(0,60.5%) minmax(540px,39.5%);align-items:start;overflow-x:hidden;background:#f5f9ff}
.login-brand{position:sticky;top:0;min-height:100vh;overflow:hidden;background:linear-gradient(135deg,#f8fbff 0%,#eef6ff 55%,#e5f1ff 100%)}
.brand-overlay{position:absolute;inset:0;z-index:1;background:radial-gradient(circle at 23% 22%,rgba(255,255,255,.95),transparent 32%),linear-gradient(115deg,rgba(247,251,255,.96),rgba(232,243,255,.72))}
.brand-campus{position:absolute;z-index:2;right:-3%;bottom:9%;width:105%;height:58%;object-fit:cover;object-position:center 44%;opacity:.26;filter:grayscale(1) sepia(1) saturate(5.5) hue-rotate(174deg) brightness(1.28) contrast(.84);mix-blend-mode:multiply;mask-image:linear-gradient(180deg,transparent 0,#000 16%,#000 76%,transparent 100%)}
.brand-water{position:absolute;z-index:3;right:-10%;bottom:-12%;width:125%;height:48%;background:repeating-radial-gradient(ellipse at 44% 100%,transparent 0 42px,rgba(69,133,213,.10) 44px 46px,transparent 48px 84px);opacity:.7}
.brand-copy{position:relative;z-index:4;padding:56px clamp(54px,4.8vw,82px) 0}
.login-wordmark{display:flex;align-items:center;color:#075ec8}
.university-wordmark{display:flex;align-items:center;gap:20px}
.university-wordmark img{width:110px;height:110px;object-fit:cover;object-position:center 4%;border-radius:50%;mix-blend-mode:multiply}
.university-wordmark div,.platform-wordmark{display:flex;flex-direction:column}
.university-wordmark strong{font-family:"LXGW WenKai Screen","KaiTi",serif;font-size:46px;line-height:1.1;letter-spacing:.08em;white-space:nowrap}
.university-wordmark span{margin-top:7px;font-size:16px;letter-spacing:.04em;white-space:nowrap}
.login-wordmark>i{width:1px;height:92px;margin:0 32px;background:#8eb7e9}
.platform-wordmark strong{font-size:50px;line-height:1.1;letter-spacing:.08em;white-space:nowrap}
.platform-wordmark span{margin-top:10px;font-size:21px;letter-spacing:.08em;white-space:nowrap}
.brand-slogan{display:flex;align-items:center;gap:20px;margin:38px 0 0 92px;color:#1768c9}
.brand-slogan span{width:64px;height:1px;background:linear-gradient(90deg,transparent,#68a2e6)}
.brand-slogan span:last-child{background:linear-gradient(90deg,#68a2e6,transparent)}
.brand-slogan p{margin:0;font-family:"LXGW WenKai Screen","KaiTi",serif;font-size:27px;letter-spacing:.18em;white-space:nowrap}
.brand-points{position:absolute;right:6.5%;bottom:9.2%;left:6.5%;z-index:5;display:grid;gap:20px;grid-template-columns:repeat(3,1fr)}
.brand-points article{display:flex;min-height:122px;align-items:center;gap:18px;padding:22px 24px;color:#265c99;background:rgba(255,255,255,.86);border:1px solid rgba(91,145,207,.16);border-radius:14px;box-shadow:0 9px 26px rgba(33,91,157,.08)}
.brand-points .el-icon{flex:0 0 auto;color:#0864d8;font-size:44px}
.brand-points article>div{display:flex;flex-direction:column}.brand-points strong{color:#0864d8;font-size:17px}.brand-points span{margin-top:7px;color:#617793;font-size:12px;line-height:1.75}
.login-panel{display:flex;min-height:100vh;align-items:flex-start;justify-content:center;padding:55px 34px;background:#f5f9ff}
.login-card{width:568px;min-height:718px;padding:30px 39px 24px;background:#fff;border:1px solid #deE8f4;border-radius:15px;box-shadow:0 14px 42px rgba(30,77,132,.12)}
.mobile-logo{display:none}.login-tabs{display:grid;grid-template-columns:1fr 1fr;margin-bottom:30px;border-bottom:1px solid #dbe5f1}
.login-tabs button{position:relative;height:52px;color:#7c889b;background:transparent;border:0;cursor:pointer;font-size:20px;font-weight:700}.login-tabs button.active{color:#0765d7}.login-tabs button.active::after{position:absolute;right:12%;bottom:-1px;left:12%;height:3px;content:'';background:#0765d7;border-radius:3px 3px 0 0}
.login-card :deep(.el-form-item){margin-bottom:25px}.login-card :deep(.el-form-item__label){height:auto;margin-bottom:9px;color:#1f2c3d;font-size:15px;font-weight:700}.login-card :deep(.el-input__wrapper){min-height:60px;padding:1px 19px;border-radius:8px}.login-card :deep(.el-input__inner){font-size:14px}.login-card :deep(.el-input__prefix){font-size:18px}
.form-title{margin-bottom:20px}.form-title h2{margin:0;color:var(--text);font-size:22px}.form-title p{margin:6px 0 0;color:var(--text-muted);font-size:13px}.form-grid{display:grid;gap:0 14px;grid-template-columns:1fr 1fr}
.captcha-row{display:flex;width:100%;align-items:center;gap:10px}.captcha-row>.el-input{min-width:0;flex:1}.captcha-button{width:132px;height:60px;flex:0 0 auto;padding:0;overflow:hidden;color:#174d8d;background:#fff;border:1px solid #dbe5f1;border-radius:8px;cursor:pointer}.captcha-button img{display:block;width:100%;height:100%;object-fit:contain}.captcha-button span{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:24px;letter-spacing:.18em}.captcha-refresh{display:grid;width:34px;height:60px;flex:0 0 auto;place-items:center;color:#73839a;background:transparent;border:0;cursor:pointer;font-size:23px}
.login-options{display:flex;align-items:center;justify-content:space-between;margin:-2px 0 25px}.login-options button{color:#0765d7;background:transparent;border:0;cursor:pointer}.submit-button{width:100%;height:60px;font-size:18px}.guest-entry{display:flex;align-items:center;justify-content:center;gap:6px;width:100%;margin:14px auto 0;color:#7c889b;font-size:14px;background:none;border:0;cursor:pointer;transition:color .2s}.guest-entry:hover{color:#0765d7}.guest-entry:disabled{cursor:not-allowed;opacity:.5}.login-footnote{margin:24px 0 0;color:#9aacc2;font-size:12px;text-align:center}
.form-fade-enter-active,.form-fade-leave-active{transition:opacity .18s ease,transform .18s ease}.form-fade-enter-from{opacity:0;transform:translateX(10px)}.form-fade-leave-to{opacity:0;transform:translateX(-10px)}
:global(html.dark .login-panel){background:#0c1420}:global(html.dark .login-card){background:#121d2b;border-color:#26384e}:global(html.dark .brand-overlay){background:linear-gradient(120deg,rgba(10,24,42,.92),rgba(12,31,55,.88))}:global(html.dark .login-card .el-form-item__label){color:#edf4ff}
@media(max-width:1440px){.university-wordmark img{width:86px;height:86px}.university-wordmark strong{font-size:34px}.university-wordmark span{font-size:12px}.platform-wordmark strong{font-size:39px}.platform-wordmark span{font-size:16px}.login-wordmark>i{height:74px;margin:0 24px}.brand-slogan{margin-left:60px}.brand-slogan p{font-size:22px}.brand-points article{min-height:102px;padding:18px}.brand-points .el-icon{font-size:36px}}
@media(max-width:1100px){.login-page{grid-template-columns:1fr}.login-brand{display:none}.login-panel{min-height:100vh;padding:30px}.login-card{min-height:auto}.mobile-logo{display:block;margin-bottom:22px}}
@media(max-width:600px){.login-panel{padding:18px}.login-card{width:100%;padding:26px 22px}.form-grid{grid-template-columns:1fr}.captcha-button{width:100px}.captcha-refresh{display:none}}
</style>
