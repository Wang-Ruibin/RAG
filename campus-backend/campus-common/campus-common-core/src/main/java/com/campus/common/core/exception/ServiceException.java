package com.campus.common.core.exception;

/**
 * 业务异常 — 抛出后由 GlobalExceptionHandler 统一处理
 *
 * @author CampusQA Team
 */
public class ServiceException extends RuntimeException {

    private static final long serialVersionUID = 1L;

    private final int code;

    public ServiceException(String message) {
        super(message);
        this.code = 500;
    }

    public ServiceException(String message, int code) {
        super(message);
        this.code = code;
    }

    public ServiceException(String message, Throwable cause) {
        super(message, cause);
        this.code = 500;
    }

    public int getCode() {
        return code;
    }
}
