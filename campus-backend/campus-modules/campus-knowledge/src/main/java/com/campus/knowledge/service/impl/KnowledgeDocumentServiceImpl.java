package com.campus.knowledge.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.campus.knowledge.domain.entity.KnowledgeDocument;
import com.campus.knowledge.mapper.KnowledgeDocumentMapper;
import com.campus.knowledge.service.IKnowledgeDocumentService;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;

@Service
public class KnowledgeDocumentServiceImpl extends ServiceImpl<KnowledgeDocumentMapper, KnowledgeDocument>
        implements IKnowledgeDocumentService {

    @Override
    public List<Map<String, Object>> search(String keyword, int limit) {
        return baseMapper.searchByKeyword(keyword, limit);
    }

    @Override
    public void incrementViewCount(Long docId) {
        KnowledgeDocument doc = this.getById(docId);
        if (doc != null) {
            doc.setViewCount((doc.getViewCount() == null ? 0 : doc.getViewCount()) + 1);
            this.updateById(doc);
        }
    }
}
