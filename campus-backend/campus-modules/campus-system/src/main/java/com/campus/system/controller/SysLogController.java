package com.campus.system.controller;

import cn.dev33.satoken.annotation.SaCheckPermission;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.campus.common.core.domain.R;
import com.campus.common.core.web.PageQuery;
import com.campus.common.excel.ExcelUtil;
import com.campus.common.log.annotation.Log;
import com.campus.system.domain.entity.SysOperLog;
import com.campus.system.domain.vo.SysOperLogExportVo;
import com.campus.system.service.ISysOperLogService;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;

/**
 * 系统日志 Controller
 */
@RestController
@RequestMapping("/system/log")
public class SysLogController {

    private final ISysOperLogService operLogService;

    public SysLogController(ISysOperLogService operLogService) {
        this.operLogService = operLogService;
    }

    @SaCheckPermission("system:log:query")
    @GetMapping("/list")
    public R<PageQuery.PageResult<SysOperLog>> list(PageQuery pageQuery, SysOperLog log) {
        IPage<SysOperLog> page = operLogService.page(pageQuery.buildPage(), buildWrapper(log));
        return R.ok(PageQuery.result(page));
    }

    @SaCheckPermission("system:log:export")
    @Log(title = "导出系统日志", businessType = 0, saveResponseData = false)
    @GetMapping("/export")
    public void export(SysOperLog log, HttpServletResponse response) {
        List<SysOperLogExportVo> rows = operLogService.list(buildWrapper(log)).stream()
                .map(SysOperLogExportVo::from)
                .toList();
        String fileName = "系统日志_" + LocalDateTime.now()
                .format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"));
        ExcelUtil.exportExcel(rows, fileName, SysOperLogExportVo.class, response);
    }

    /** 列表与导出共用的查询条件 */
    private LambdaQueryWrapper<SysOperLog> buildWrapper(SysOperLog log) {
        return new LambdaQueryWrapper<SysOperLog>()
                .like(log.getTitle() != null, SysOperLog::getTitle, log.getTitle())
                .like(log.getOperName() != null, SysOperLog::getOperName, log.getOperName())
                .eq(log.getStatus() != null, SysOperLog::getStatus, log.getStatus())
                .orderByDesc(SysOperLog::getOperTime);
    }

    @SaCheckPermission("system:log:remove")
    @Log(title = "删除系统日志", businessType = 3)
    @DeleteMapping("/{operIds}")
    public R<Void> remove(@PathVariable("operIds") List<Long> operIds) {
        operLogService.deleteLogs(operIds);
        return R.ok();
    }

    @SaCheckPermission("system:log:remove")
    @Log(title = "清空系统日志", businessType = 3)
    @DeleteMapping("/clean")
    public R<Void> clean() {
        operLogService.cleanLog();
        return R.ok();
    }
}
