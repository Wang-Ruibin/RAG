package com.campus.knowledge.controller;

import cn.dev33.satoken.annotation.SaCheckPermission;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.campus.common.core.domain.R;
import com.campus.common.core.web.PageQuery;
import com.campus.common.log.annotation.Log;
import com.campus.knowledge.domain.entity.KnowledgeDocument;
import com.campus.knowledge.service.IKnowledgeDocumentService;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * 知识文档管理
 */
@RestController
@RequestMapping("/knowledge/document")
public class DocumentController {

    private final IKnowledgeDocumentService documentService;

    public DocumentController(IKnowledgeDocumentService documentService) {
        this.documentService = documentService;
    }

    /**
     * 分页查询文档
     */
    @SaCheckPermission("knowledge:document:list")
    @GetMapping("/list")
    public R<PageQuery.PageResult<KnowledgeDocument>> list(PageQuery pageQuery,
                                                            @RequestParam(required = false) String title,
                                                            @RequestParam(required = false) Long categoryId,
                                                            @RequestParam(required = false) String status) {
        IPage<KnowledgeDocument> page = documentService.page(pageQuery.buildPage(),
                new LambdaQueryWrapper<KnowledgeDocument>()
                        .like(title != null, KnowledgeDocument::getTitle, title)
                        .eq(categoryId != null, KnowledgeDocument::getCategoryId, categoryId)
                        .eq(status != null, KnowledgeDocument::getStatus, status)
                        .orderByDesc(KnowledgeDocument::getCreateTime));
        return R.ok(PageQuery.result(page));
    }

    /**
     * 文档详情
     */
    @SaCheckPermission("knowledge:document:query")
    @GetMapping("/{docId}")
    public R<KnowledgeDocument> detail(@PathVariable("docId") Long docId) {
        documentService.incrementViewCount(docId);
        return R.ok(documentService.getById(docId));
    }

    @SaCheckPermission("knowledge:document:add")
    @Log(title = "新增知识文档", businessType = 1)
    @PostMapping
    public R<Void> add(@RequestBody KnowledgeDocument doc) {
        doc.setViewCount(0);
        doc.setStatus("1");
        documentService.save(doc);
        return R.ok();
    }

    @SaCheckPermission("knowledge:document:edit")
    @Log(title = "修改知识文档", businessType = 2)
    @PutMapping
    public R<Void> edit(@RequestBody KnowledgeDocument doc) {
        documentService.updateById(doc);
        return R.ok();
    }

    @SaCheckPermission("knowledge:document:remove")
    @Log(title = "删除知识文档", businessType = 3)
    @DeleteMapping("/{docIds}")
    public R<Void> remove(@PathVariable("docIds") List<Long> docIds) {
        documentService.removeByIds(docIds);
        return R.ok();
    }

    /**
     * 关键词搜索（供 RAG 调用）
     */
    @GetMapping("/search")
    public R<List<Map<String, Object>>> search(@RequestParam String keyword,
                                                @RequestParam(defaultValue = "5") int limit) {
        return R.ok(documentService.search(keyword, limit));
    }
}
