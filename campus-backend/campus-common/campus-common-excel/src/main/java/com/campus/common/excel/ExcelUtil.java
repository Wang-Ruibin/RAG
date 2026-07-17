package com.campus.common.excel;

import com.alibaba.excel.EasyExcel;
import com.campus.common.core.exception.ServiceException;
import jakarta.servlet.http.HttpServletResponse;

import java.io.IOException;
import java.io.InputStream;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.List;

/**
 * Excel 导入导出工具（EasyExcel 封装）
 *
 * <p>导出：实体/VO 上用 {@code @ExcelProperty("列名")} 标注列，
 * Controller 中一行 {@code ExcelUtil.exportExcel(list, "文件名", Vo.class, response)} 完成下载。
 * 不想导出的字段加 {@code @ExcelIgnore}。</p>
 *
 * <p>导入：{@code List<Vo> rows = ExcelUtil.importExcel(file.getInputStream(), Vo.class)}</p>
 */
public class ExcelUtil {

    private ExcelUtil() {}

    /**
     * 导出 Excel 并写入 HTTP 响应（浏览器直接下载 .xlsx）
     *
     * @param list      数据列表
     * @param fileName  文件名（不含扩展名），同时作为 sheet 名
     * @param clazz     带 @ExcelProperty 注解的 VO 类型
     * @param response  HTTP 响应
     */
    public static <T> void exportExcel(List<T> list, String fileName, Class<T> clazz,
                                       HttpServletResponse response) {
        try {
            response.setContentType(
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
            response.setCharacterEncoding("utf-8");
            // RFC 5987 编码，兼容中文文件名
            String encoded = URLEncoder.encode(fileName, StandardCharsets.UTF_8)
                    .replaceAll("\\+", "%20");
            response.setHeader("Content-Disposition",
                    "attachment;filename*=utf-8''" + encoded + ".xlsx");
            EasyExcel.write(response.getOutputStream(), clazz)
                    .autoCloseStream(false)
                    .sheet(fileName)
                    .doWrite(list);
        } catch (IOException e) {
            throw new ServiceException("导出 Excel 失败: " + e.getMessage());
        }
    }

    /**
     * 同步读取 Excel 全部行（首行为表头，按 @ExcelProperty 匹配）
     */
    public static <T> List<T> importExcel(InputStream inputStream, Class<T> clazz) {
        return EasyExcel.read(inputStream).head(clazz).sheet().doReadSync();
    }
}
