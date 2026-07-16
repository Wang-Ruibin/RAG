package com.campus.knowledge.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.campus.knowledge.domain.entity.KnowledgeDocument;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;
import java.util.Map;

public interface KnowledgeDocumentMapper extends BaseMapper<KnowledgeDocument> {

    @Select("SELECT d.doc_id, d.title, d.content, d.keywords, c.category_name " +
            "FROM campus_knowledge_document d " +
            "LEFT JOIN campus_knowledge_category c ON d.category_id = c.category_id " +
            "WHERE d.status = '1' AND d.del_flag = '0' " +
            "AND (d.title LIKE CONCAT('%',#{keyword},'%') OR d.content LIKE CONCAT('%',#{keyword},'%') " +
            "OR d.keywords LIKE CONCAT('%',#{keyword},'%')) " +
            "ORDER BY d.view_count DESC LIMIT #{limit}")
    List<Map<String, Object>> searchByKeyword(@Param("keyword") String keyword, @Param("limit") int limit);
}
