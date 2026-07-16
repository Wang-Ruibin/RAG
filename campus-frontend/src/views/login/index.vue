<template>
  <div class="login-page" @mousemove="onParallax">
    <!-- ============ 左：青绿山水品牌面板（纯视觉，无逻辑） ============ -->
    <div class="brand-panel" aria-hidden="true">
      <!-- 远山近峦：三层山影，大气透视（远淡近深），随鼠标轻微视差 -->
      <svg class="mountains" viewBox="0 0 1200 800" preserveAspectRatio="xMidYMax slice">
        <defs>
          <!-- 月晕 -->
          <radialGradient id="moonHalo">
            <stop offset="0%" stop-color="rgba(232, 213, 163, 0.30)" />
            <stop offset="100%" stop-color="rgba(232, 213, 163, 0)" />
          </radialGradient>
          <!-- 山体渐变：山脊承月光、山脚入夜雾 -->
          <linearGradient id="mFar" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#4F8E78" />
            <stop offset="45%" stop-color="#2E6152" />
            <stop offset="100%" stop-color="#1D453A" />
          </linearGradient>
          <linearGradient id="mMid" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#38735E" />
            <stop offset="50%" stop-color="#214E3F" />
            <stop offset="100%" stop-color="#133128" />
          </linearGradient>
          <linearGradient id="mNear" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#235244" />
            <stop offset="50%" stop-color="#16382E" />
            <stop offset="100%" stop-color="#0C231C" />
          </linearGradient>
        </defs>

        <!-- 绢金月轮 + 月晕 -->
        <circle class="moon-halo" cx="880" cy="180" r="150" fill="url(#moonHalo)" />
        <circle class="moon" cx="880" cy="180" r="52" />

        <!-- 远山：主峰在左中，余脉绵延，雾气半透融入天色 -->
        <path class="mt mt-far"
          d="M0 480 L45 462 L90 470 L140 440 L180 452 L230 415 L280 430 L330 380 L365 350 L385 342 L410 365 L440 355 L470 390 L510 405 L545 392 L590 430 L640 415 L690 445 L730 420 L770 400 L805 378 L830 370 L860 392 L890 385 L930 420 L975 435 L1020 425 L1070 455 L1120 445 L1170 470 L1200 462 L1200 800 L0 800 Z" />
        <!-- 中山：左肩右峰，两段主脊 -->
        <path class="mt mt-mid"
          d="M0 590 L40 570 L80 545 L120 520 L155 498 L185 485 L205 480 L235 502 L265 495 L300 528 L340 545 L385 535 L430 565 L480 555 L530 585 L580 570 L630 595 L680 580 L720 600 L760 585 L800 560 L840 540 L880 512 L915 488 L945 465 L965 460 L990 480 L1020 472 L1055 500 L1095 520 L1140 545 L1180 560 L1200 555 L1200 800 L0 800 Z" />
        <!-- 近山：最暗剪影，主峰居中偏左 -->
        <path class="mt mt-near"
          d="M0 660 L50 640 L100 618 L140 600 L175 610 L215 592 L260 615 L310 635 L360 622 L410 648 L460 630 L510 600 L550 575 L580 562 L610 580 L645 572 L685 605 L730 625 L775 615 L820 645 L870 660 L920 650 L970 675 L1030 662 L1080 685 L1140 675 L1200 695 L1200 800 L0 800 Z" />
      </svg>

      <!-- 云雾 -->
      <div class="mist mist-1"></div>
      <div class="mist mist-2"></div>

      <!-- 水面：月光倒影 + 两层错动波纹 -->
      <div class="water">
        <div class="moon-glint"></div>
        <svg class="wave wave-1" viewBox="0 0 2400 60" preserveAspectRatio="none">
          <path d="M0 30 Q150 10 300 30 T600 30 T900 30 T1200 30 T1500 30 T1800 30 T2100 30 T2400 30 V60 H0 Z" />
        </svg>
        <svg class="wave wave-2" viewBox="0 0 2400 60" preserveAspectRatio="none">
          <path d="M0 35 Q200 15 400 35 T800 35 T1200 35 T1600 35 T2000 35 T2400 35 V60 H0 Z" />
        </svg>
      </div>

      <!-- 品牌文案 -->
      <div class="brand-content">
        <p class="eyebrow">河海大学 · 校园知识问答</p>
        <h1 class="brand-title">
          河海智问<span class="latin">QA</span>
        </h1>
        <p class="brand-sub">千川汇海，一问即答</p>
        <div class="seal">智问</div>
      </div>
    </div>

    <!-- ============ 右：表单面板 ============ -->
    <div class="form-panel">
      <Transition name="form-swap" mode="out-in">
        <!-- 登录表单 -->
        <div v-if="!isRegister" key="login" class="form-box">
          <div class="card-header">
            <h2>欢迎回来</h2>
            <p>登录你的河海智问账号</p>
          </div>
          <el-form ref="formRef" :model="form" :rules="rules" size="large" @keyup.enter="handleLogin">
            <el-form-item prop="username">
              <el-input v-model="form.username" placeholder="请输入用户名" :prefix-icon="User" />
            </el-form-item>
            <el-form-item prop="password">
              <el-input v-model="form.password" type="password" placeholder="请输入密码"
                show-password :prefix-icon="Lock" />
            </el-form-item>
            <el-form-item prop="code">
              <div class="captcha-row">
                <el-input v-model="form.code" placeholder="验证码" :prefix-icon="Key" />
                <img :src="captchaImg" class="captcha-img" @click="refreshCaptcha" title="点击刷新" />
              </div>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="loading" @click="handleLogin" class="login-btn">
                {{ loading ? '登录中...' : '登 录' }}
              </el-button>
            </el-form-item>
          </el-form>
          <div class="card-footer">
            <span @click="isRegister = true; resetForm()">没有账号？立即注册</span>
          </div>
        </div>

        <!-- 注册表单 -->
        <div v-else key="register" class="form-box">
          <div class="card-header">
            <h2>创建账号</h2>
            <p>加入河海智问知识社区</p>
          </div>
          <el-form ref="regRef" :model="regForm" :rules="regRules" size="large" @keyup.enter="handleRegister">
            <el-form-item prop="username">
              <el-input v-model="regForm.username" placeholder="请输入用户名" :prefix-icon="User" />
            </el-form-item>
            <el-form-item prop="nickName">
              <el-input v-model="regForm.nickName" placeholder="请输入昵称" :prefix-icon="Edit" />
            </el-form-item>
            <el-form-item prop="email">
              <el-input v-model="regForm.email" placeholder="请输入邮箱" :prefix-icon="Message" />
            </el-form-item>
            <el-form-item prop="phone">
              <el-input v-model="regForm.phone" placeholder="请输入手机号" :prefix-icon="Iphone" />
            </el-form-item>
            <el-form-item prop="password">
              <el-input v-model="regForm.password" type="password" placeholder="请输入密码"
                show-password :prefix-icon="Lock" />
            </el-form-item>
            <el-form-item prop="confirmPwd">
              <el-input v-model="regForm.confirmPwd" type="password" placeholder="确认密码"
                show-password :prefix-icon="Lock" />
            </el-form-item>
            <el-form-item prop="code">
              <div class="captcha-row">
                <el-input v-model="regForm.code" placeholder="验证码" :prefix-icon="Key" />
                <img :src="captchaImg" class="captcha-img" @click="refreshCaptcha" title="点击刷新" />
              </div>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="loading" @click="handleRegister" class="login-btn">
                {{ loading ? '注册中...' : '注 册' }}
              </el-button>
            </el-form-item>
          </el-form>
          <div class="card-footer">
            <span @click="isRegister = false; resetForm()">已有账号？去登录</span>
          </div>
        </div>
      </Transition>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { getCaptcha, register as registerApi } from '@/api/auth'
import { ElMessage } from 'element-plus'
import { User, Lock, Key, Edit, Message, Iphone } from '@element-plus/icons-vue'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref()
const regRef = ref()
const loading = ref(false)
const isRegister = ref(false)
const captchaImg = ref('')
const captchaUuid = ref('')

// 鼠标视差（纯视觉）：写入 CSS 变量，山峦/云雾各自取用
const parallax = reactive({ x: 0, y: 0 })
function onParallax(e: MouseEvent) {
  parallax.x = (e.clientX / window.innerWidth - 0.5) * 2
  parallax.y = (e.clientY / window.innerHeight - 0.5) * 2
  const el = e.currentTarget as HTMLElement
  el.style.setProperty('--mx', String(parallax.x))
  el.style.setProperty('--my', String(parallax.y))
}

const form = reactive({ username: '', password: '', code: '' })
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  code: [{ required: true, message: '请输入验证码', trigger: 'blur' }]
}

const regForm = reactive({ username: '', nickName: '', email: '', phone: '', password: '', confirmPwd: '', code: '' })
const validateConfirm = (_rule: any, value: string, cb: any) => {
  if (value !== regForm.password) cb(new Error('两次密码不一致'))
  else cb()
}
const regRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  nickName: [{ required: true, message: '请输入昵称', trigger: 'blur' }],
  email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }],
  phone: [{ required: true, message: '请输入手机号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  confirmPwd: [{ required: true, message: '请确认密码', trigger: 'blur' }, { validator: validateConfirm, trigger: 'blur' }],
  code: [{ required: true, message: '请输入验证码', trigger: 'blur' }]
}

async function refreshCaptcha() {
  try {
    const res = await getCaptcha()
    captchaUuid.value = res.data.uuid
    captchaImg.value = res.data.img
  } catch { /* captcha failed silently */ }
}

function resetForm() {
  form.username = ''; form.password = ''; form.code = ''
  regForm.username = ''; regForm.nickName = ''; regForm.email = ''; regForm.phone = ''
  regForm.password = ''; regForm.confirmPwd = ''; regForm.code = ''
  refreshCaptcha()
}

async function handleLogin() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    await userStore.login(form.username, form.password, captchaUuid.value, form.code)
    ElMessage.success('登录成功')
    router.push('/home')
  } catch {
    refreshCaptcha()
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  const valid = await regRef.value?.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    await registerApi({
      username: regForm.username,
      password: regForm.password,
      nickName: regForm.nickName,
      email: regForm.email,
      phone: regForm.phone,
      uuid: captchaUuid.value,
      code: regForm.code
    })
    ElMessage.success('注册成功，请登录')
    isRegister.value = false
    form.username = regForm.username
    regForm.username = ''; regForm.nickName = ''; regForm.email = ''; regForm.phone = ''
    regForm.password = ''; regForm.confirmPwd = ''; regForm.code = ''
    refreshCaptcha()
  } catch {
    refreshCaptcha()
  } finally {
    loading.value = false
  }
}

onMounted(refreshCaptcha)
</script>

<style scoped lang="scss">
// ============================================================
// 「青绿山水」登录页：左山水长卷 · 右宣纸表单
// ============================================================
.login-page {
  --mx: 0;
  --my: 0;
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: var(--bg);
}

// ---------- 左侧：山水品牌面板 ----------
.brand-panel {
  position: relative;
  flex: 1.25;
  min-width: 0;
  overflow: hidden;
  background: linear-gradient(175deg, #0A1A16 0%, #0E2A22 55%, #10382C 100%);
}

.mountains {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;

  .moon {
    fill: #E8D5A3;
    opacity: 0.9;
    filter: drop-shadow(0 0 22px rgba(232, 213, 163, 0.5));
    animation: moon-rise 1.6s cubic-bezier(0.22, 1, 0.36, 1) both;
  }
  .moon-halo {
    animation: moon-rise 1.6s cubic-bezier(0.22, 1, 0.36, 1) both;
  }
  .mt {
    transition: transform 0.35s ease-out;
    // 月光勾勒山脊线
    stroke: rgba(226, 245, 235, 0.14);
    stroke-width: 1.5;
    paint-order: stroke;
  }
  .mt-far {
    fill: url(#mFar);
    opacity: 0.8;
    transform: translate(calc(var(--mx) * -6px), calc(var(--my) * -3px));
    animation: mt-in 1.1s cubic-bezier(0.22, 1, 0.36, 1) 0.1s both;
  }
  .mt-mid {
    fill: url(#mMid);
    opacity: 0.94;
    transform: translate(calc(var(--mx) * -14px), calc(var(--my) * -6px));
    animation: mt-in 1.1s cubic-bezier(0.22, 1, 0.36, 1) 0.25s both;
  }
  .mt-near {
    fill: url(#mNear);
    stroke: rgba(226, 245, 235, 0.08);
    transform: translate(calc(var(--mx) * -24px), calc(var(--my) * -10px));
    animation: mt-in 1.1s cubic-bezier(0.22, 1, 0.36, 1) 0.4s both;
  }
}

@keyframes moon-rise {
  from { opacity: 0; transform: translateY(30px); }
  to   { opacity: 0.85; transform: translateY(0); }
}
@keyframes mt-in {
  from { opacity: 0; transform: translateY(60px); }
}

// 云雾：横向漂移
.mist {
  position: absolute;
  border-radius: 50%;
  filter: blur(46px);
  background: rgba(220, 240, 230, 0.10);
  pointer-events: none;
  &.mist-1 {
    width: 480px; height: 120px;
    top: 46%; left: 8%;
    animation: mist-drift 22s ease-in-out infinite;
  }
  &.mist-2 {
    width: 380px; height: 100px;
    top: 62%; right: 4%;
    animation: mist-drift 28s ease-in-out infinite reverse;
  }
}
@keyframes mist-drift {
  0%, 100% { transform: translateX(0); opacity: 0.7; }
  50%      { transform: translateX(70px); opacity: 1; }
}

// 水面波纹：两层错速平移
.water {
  position: absolute;
  left: 0; right: 0; bottom: 0;
  height: 90px;
  // 月光洒在水面的碎金倒影：两段横卧的柔光椭圆
  .moon-glint {
    position: absolute;
    left: 68%;
    bottom: 30px;
    width: 130px;
    height: 38px;
    background: radial-gradient(ellipse at center,
      rgba(232, 213, 163, 0.35), rgba(232, 213, 163, 0.08) 55%, transparent 72%);
    filter: blur(6px);
    animation: glint-shimmer 5s ease-in-out infinite;
    &::after {
      content: '';
      position: absolute;
      left: 18%;
      bottom: -20px;
      width: 64%;
      height: 14px;
      background: radial-gradient(ellipse at center,
        rgba(232, 213, 163, 0.22), transparent 70%);
    }
  }
  .wave {
    position: absolute;
    bottom: 0;
    width: 200%;
    height: 100%;
    path { fill: rgba(150, 220, 190, 0.10); }
    &.wave-1 { animation: wave-move 13s linear infinite; }
    &.wave-2 {
      bottom: -14px;
      path { fill: rgba(150, 220, 190, 0.14); }
      animation: wave-move 8s linear infinite reverse;
    }
  }
}
@keyframes wave-move {
  from { transform: translateX(0); }
  to   { transform: translateX(-50%); }
}
@keyframes glint-shimmer {
  0%, 100% { opacity: 0.7; transform: scaleX(1); }
  50%      { opacity: 1; transform: scaleX(1.15); }
}

// 品牌文案
.brand-content {
  position: relative;
  z-index: 2;
  padding: 12vh 8% 0;
  color: #F2F7F0;

  .eyebrow {
    margin: 0 0 18px;
    font-size: 13px;
    letter-spacing: 0.35em;
    color: rgba(220, 240, 230, 0.62);
    animation: rise-in 0.8s cubic-bezier(0.22, 1, 0.36, 1) 0.2s both;
  }

  .brand-title {
    margin: 0;
    font-family: var(--font-display);
    font-size: clamp(44px, 5.6vw, 76px);
    font-weight: 700;
    line-height: 1.15;
    letter-spacing: 0.06em;
    color: #F5FAF4;
    text-shadow: 0 4px 30px rgba(0, 0, 0, 0.35);
    animation: rise-in 0.9s cubic-bezier(0.22, 1, 0.36, 1) 0.35s both;

    .latin {
      margin-left: 10px;
      font-family: var(--font-body);
      font-weight: 800;
      font-size: 0.55em;
      vertical-align: 0.14em;
      letter-spacing: 0.02em;
      background: linear-gradient(120deg, #6FDCB4, #B9E8A0);
      -webkit-background-clip: text;
      background-clip: text;
      color: transparent;
    }
  }

  .brand-sub {
    margin: 20px 0 0;
    font-family: var(--font-display);
    font-size: clamp(16px, 1.5vw, 20px);
    letter-spacing: 0.2em;
    color: rgba(220, 240, 230, 0.78);
    animation: rise-in 0.9s cubic-bezier(0.22, 1, 0.36, 1) 0.5s both;
  }

  // 朱砂印章：延迟“钤印”入场
  .seal {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    margin-top: 34px;
    width: 58px;
    height: 58px;
    font-family: var(--font-display);
    font-size: 21px;
    font-weight: 700;
    line-height: 1.15;
    letter-spacing: 0.08em;
    color: #FBEFEA;
    background: var(--seal, #C4472F);
    border-radius: 8px;
    transform: rotate(-4deg);
    box-shadow: 0 6px 20px rgba(196, 71, 47, 0.4), inset 0 0 0 2px rgba(251, 239, 234, 0.35);
    animation: seal-stamp 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) 1s both;
  }
}

@keyframes rise-in {
  from { opacity: 0; transform: translateY(20px); }
  to   { opacity: 1; transform: translateY(0); }
}
@keyframes seal-stamp {
  0%   { opacity: 0; transform: rotate(-4deg) scale(1.7); }
  60%  { opacity: 1; transform: rotate(-4deg) scale(0.94); }
  100% { opacity: 1; transform: rotate(-4deg) scale(1); }
}

// ---------- 右侧：表单面板 ----------
.form-panel {
  width: clamp(400px, 36vw, 520px);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 48px;
  overflow-y: auto;
  background: var(--bg);
  // 纸面肌理：极淡青竹晕染
  background-image:
    radial-gradient(600px 300px at 110% -10%, rgba(15, 145, 121, 0.06), transparent 65%),
    radial-gradient(500px 260px at -10% 110%, rgba(82, 199, 155, 0.05), transparent 65%);
}

.form-box {
  width: 100%;
  max-width: 350px;

  .card-header {
    margin-bottom: 30px;
    h2 {
      display: flex;
      align-items: center;
      margin: 0 0 8px;
      font-family: var(--font-display);
      font-size: 28px;
      font-weight: 700;
      letter-spacing: 0.04em;
      color: var(--primary);
      // 朱砂小印点呼应品牌面板
      &::before {
        content: '';
        width: 10px;
        height: 10px;
        margin-right: 12px;
        background: var(--seal, #C4472F);
        border-radius: 3px;
        transform: rotate(45deg);
        flex-shrink: 0;
      }
    }
    p {
      margin: 0 0 0 22px;
      font-size: 14px;
      color: var(--text-secondary);
    }
  }

  .captcha-row {
    display: flex;
    gap: 10px;
    width: 100%;
    .el-input { flex: 1; }
    .captcha-img {
      width: 110px;
      height: 40px;
      border-radius: 10px;
      cursor: pointer;
      border: 1px solid var(--border);
      transition: border-color 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease;
      &:hover {
        border-color: var(--accent);
        transform: scale(1.02);
        box-shadow: 0 2px 10px var(--ring);
      }
    }
  }

  .login-btn {
    width: 100%;
    height: 46px;
    border: none;
    border-radius: 12px;
    font-size: 15px;
    font-weight: 600;
    letter-spacing: 6px;
    background: var(--grad);
    box-shadow: var(--glow);
    transition: all 0.25s cubic-bezier(0.22, 1, 0.36, 1);
    &:hover {
      box-shadow: var(--glow-lg);
      filter: brightness(1.06);
      transform: translateY(-2px);
    }
    &:active { transform: translateY(0) scale(0.98); }
  }

  .card-footer {
    text-align: center;
    font-size: 13px;
    color: var(--accent);
    cursor: pointer;
    transition: opacity 0.2s ease;
    &:hover { opacity: 0.75; text-decoration: underline; text-underline-offset: 4px; }
  }
}

// 登录 ↔ 注册 切换：滑动交叠
.form-swap-enter-active {
  transition: opacity 0.3s ease, transform 0.35s cubic-bezier(0.22, 1, 0.36, 1);
}
.form-swap-leave-active {
  transition: opacity 0.18s ease, transform 0.2s ease;
}
.form-swap-enter-from {
  opacity: 0;
  transform: translateX(26px);
}
.form-swap-leave-to {
  opacity: 0;
  transform: translateX(-18px);
}

// ---------- 响应式：窄屏收起山水，表单铺满 ----------
@media (max-width: 900px) {
  .brand-panel { display: none; }
  .form-panel {
    width: 100%;
    padding: 32px 24px;
  }
}

// ---------- 无障碍 ----------
@media (prefers-reduced-motion: reduce) {
  .mist, .wave, .moon, .moon-halo, .moon-glint, .mt, .seal,
  .brand-content .eyebrow, .brand-content .brand-title, .brand-content .brand-sub {
    animation: none !important;
  }
  .mountains .mt { transition: none; }
}
</style>
