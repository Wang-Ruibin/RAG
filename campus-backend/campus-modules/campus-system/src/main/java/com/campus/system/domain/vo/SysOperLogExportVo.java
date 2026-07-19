package com.campus.system.domain.vo;

import com.alibaba.excel.annotation.ExcelProperty;
import com.alibaba.excel.annotation.write.style.ColumnWidth;
import com.campus.system.domain.entity.SysOperLog;

import java.time.format.DateTimeFormatter;
import java.util.Map;

/**
 * 系统日志导出 VO（列名/宽度由 EasyExcel 注解控制）
 */
public class SysOperLogExportVo {

    private static final DateTimeFormatter TIME_FORMAT =
            DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    private static final Map<Integer, String> BUSINESS_TYPE = Map.of(
            0, "其它", 1, "新增", 2, "修改", 3, "删除", 4, "查询");

    @ExcelProperty("日志ID")
    @ColumnWidth(10)
    private Long operId;

    @ExcelProperty("操作模块")
    @ColumnWidth(22)
    private String title;

    @ExcelProperty("业务类型")
    @ColumnWidth(10)
    private String businessType;

    @ExcelProperty("操作人")
    @ColumnWidth(14)
    private String operName;

    @ExcelProperty("请求方式")
    @ColumnWidth(10)
    private String requestMethod;

    @ExcelProperty("请求URL")
    @ColumnWidth(32)
    private String operUrl;

    @ExcelProperty("操作IP")
    @ColumnWidth(16)
    private String operIp;

    @ExcelProperty("状态")
    @ColumnWidth(8)
    private String status;

    @ExcelProperty("错误信息")
    @ColumnWidth(30)
    private String errorMsg;

    @ExcelProperty("耗时(ms)")
    @ColumnWidth(10)
    private Long costTime;

    @ExcelProperty("操作时间")
    @ColumnWidth(20)
    private String operTime;

    public static SysOperLogExportVo from(SysOperLog log) {
        SysOperLogExportVo vo = new SysOperLogExportVo();
        vo.operId = log.getOperId();
        vo.title = log.getTitle();
        vo.businessType = BUSINESS_TYPE.getOrDefault(log.getBusinessType(), "其它");
        vo.operName = log.getOperName();
        vo.requestMethod = log.getRequestMethod();
        vo.operUrl = log.getOperUrl();
        vo.operIp = log.getOperIp();
        vo.status = log.getStatus() != null && log.getStatus() == 1 ? "正常" : "异常";
        vo.errorMsg = log.getErrorMsg();
        vo.costTime = log.getCostTime();
        vo.operTime = log.getOperTime() == null ? "" : log.getOperTime().format(TIME_FORMAT);
        return vo;
    }

    public Long getOperId() { return operId; }
    public String getTitle() { return title; }
    public String getBusinessType() { return businessType; }
    public String getOperName() { return operName; }
    public String getRequestMethod() { return requestMethod; }
    public String getOperUrl() { return operUrl; }
    public String getOperIp() { return operIp; }
    public String getStatus() { return status; }
    public String getErrorMsg() { return errorMsg; }
    public Long getCostTime() { return costTime; }
    public String getOperTime() { return operTime; }
}
