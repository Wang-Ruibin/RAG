package com.campus.system.controller;

import cn.dev33.satoken.annotation.SaCheckPermission;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.campus.common.core.domain.R;
import com.campus.common.core.web.PageQuery;
import com.campus.common.log.annotation.Log;
import com.campus.system.domain.entity.SysOperLog;
import com.campus.system.service.ISysOperLogService;
import org.springframework.web.bind.annotation.*;

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
        IPage<SysOperLog> page = operLogService.page(pageQuery.buildPage(),
                new LambdaQueryWrapper<SysOperLog>()
                        .like(log.getTitle() != null, SysOperLog::getTitle, log.getTitle())
                        .like(log.getOperName() != null, SysOperLog::getOperName, log.getOperName())
                        .eq(log.getStatus() != null, SysOperLog::getStatus, log.getStatus())
                        .orderByDesc(SysOperLog::getOperTime));
        return R.ok(PageQuery.result(page));
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
