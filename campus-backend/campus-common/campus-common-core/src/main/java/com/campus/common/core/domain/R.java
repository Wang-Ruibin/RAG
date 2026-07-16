package com.campus.common.core.domain;

import java.io.Serializable;

/**
 * 统一响应格式
 *
 * @param <T> 数据类型
 * @author CampusQA Team
 */
public class R<T> implements Serializable {

    private static final long serialVersionUID = 1L;

    /** 状态码 */
    public static final int SUCCESS = 200;
    public static final int FAIL = 500;
    public static final int UNAUTHORIZED = 401;
    public static final int FORBIDDEN = 403;

    private int code;
    private String msg;
    private T data;

    private R() {}

    // ==================== 静态工厂方法 ====================

    public static <T> R<T> ok() {
        return restResult(null, SUCCESS, "操作成功");
    }

    public static <T> R<T> ok(T data) {
        return restResult(data, SUCCESS, "操作成功");
    }

    public static <T> R<T> ok(T data, String msg) {
        return restResult(data, SUCCESS, msg);
    }

    public static <T> R<T> fail() {
        return restResult(null, FAIL, "操作失败");
    }

    public static <T> R<T> fail(String msg) {
        return restResult(null, FAIL, msg);
    }

    public static <T> R<T> fail(int code, String msg) {
        return restResult(null, code, msg);
    }

    public static <T> R<T> unauthorized(String msg) {
        return restResult(null, UNAUTHORIZED, msg);
    }

    public static <T> R<T> forbidden(String msg) {
        return restResult(null, FORBIDDEN, msg);
    }

    private static <T> R<T> restResult(T data, int code, String msg) {
        R<T> r = new R<>();
        r.code = code;
        r.msg = msg;
        r.data = data;
        return r;
    }

    // ==================== Getters & Setters ====================

    public int getCode() { return code; }
    public void setCode(int code) { this.code = code; }

    public String getMsg() { return msg; }
    public void setMsg(String msg) { this.msg = msg; }

    public T getData() { return data; }
    public void setData(T data) { this.data = data; }

    // ==================== 便捷判断 ====================

    public boolean isSuccess() {
        return this.code == SUCCESS;
    }

    @Override
    public String toString() {
        return "R{code=" + code + ", msg='" + msg + "', data=" + data + "}";
    }
}
