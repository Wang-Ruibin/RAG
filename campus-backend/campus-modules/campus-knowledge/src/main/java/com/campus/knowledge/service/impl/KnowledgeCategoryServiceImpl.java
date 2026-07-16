package com.campus.knowledge.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.campus.knowledge.domain.entity.KnowledgeCategory;
import com.campus.knowledge.domain.entity.KnowledgeDocument;
import com.campus.knowledge.mapper.KnowledgeCategoryMapper;
import com.campus.knowledge.mapper.KnowledgeDocumentMapper;
import com.campus.knowledge.service.IKnowledgeCategoryService;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class KnowledgeCategoryServiceImpl extends ServiceImpl<KnowledgeCategoryMapper, KnowledgeCategory>
        implements IKnowledgeCategoryService {

    private final KnowledgeDocumentMapper documentMapper;

    public KnowledgeCategoryServiceImpl(KnowledgeDocumentMapper documentMapper) {
        this.documentMapper = documentMapper;
    }

    @Override
    public List<KnowledgeCategory> getTree() {
        return this.list(new LambdaQueryWrapper<KnowledgeCategory>()
                .eq(KnowledgeCategory::getStatus, "1")
                .orderByAsc(KnowledgeCategory::getSortOrder));
    }

    @Override
    public long getDocCount(Long categoryId) {
        return documentMapper.selectCount(
                new LambdaQueryWrapper<KnowledgeDocument>()
                        .eq(KnowledgeDocument::getCategoryId, categoryId)
                        .eq(KnowledgeDocument::getStatus, "1"));
    }
}
