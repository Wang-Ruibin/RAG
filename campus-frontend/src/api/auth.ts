import request from './request'
import type { R, LoginForm, RegisterForm, LoginResult, UserInfo, CaptchaResult } from '@/types'

export function login(data: LoginForm): Promise<R<LoginResult>> {
  return request.post('/auth/login', data)
}

export function register(data: RegisterForm): Promise<R<void>> {
  return request.post('/auth/register', data)
}

/** 访客登录 —— 免验证码免密码，拿真 token（roles=[guest]），问答不落库 */
export function guestLogin(): Promise<R<LoginResult>> {
  return request.post('/auth/guest-login')
}

export function getCaptcha(): Promise<R<CaptchaResult>> {
  return request.get('/auth/captcha')
}

export function getUserInfo(): Promise<R<UserInfo>> {
  return request.get('/auth/getInfo')
}
