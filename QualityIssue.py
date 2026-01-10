import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime
from PIL import Image
import io
from st-gsheets-connection import GSheetsConnection

# --- 1. 初始化 Google Sheets 连接 (解决 conn 未定义问题) ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. 配置与多语言字典 ---
LANG = {
    "中文": {
        "title": "品质问题记录表", "proj_id": "项目ID", "order_id": "工单号", 
        "name": "项目名称", "cat": "问题分类", "desc": "问题描述", 
        "dept": "责任部门", "owner": "跟进人", "res": "处理结果", 
        "img": "问题图片", "rem": "备注", "date": "记录日期", 
        "rec": "记录人", "export": "导出PDF", "save": "保存到云端",
        "confirm": "预览并确认", "total": "总计条数", "sum_cat": "分类统计"
    },
    "English": {
        "title": "Quality Issue Report", "proj_id": "Project ID", "order_id": "Work Order", 
        "name": "Project Name", "cat": "Category", "desc": "Description", 
        "dept": "Department", "owner": "Follower", "res": "Result", 
        "img": "Image", "rem": "Remark", "date": "Date", 
        "rec": "Recorder", "export": "Export PDF", "save": "Save to Cloud",
        "confirm": "Preview & Confirm", "total": "Total Issues", "sum_cat": "Summary by Category"
    },
    "Tiếng Việt": {
        "title": "Bảng ghi chép vấn đề chất lượng", "proj_id": "Mã dự án", "order_id": "Số lệnh", 
        "name": "Tên dự án", "cat": "Phân loại", "desc": "Mô tả", 
        "dept": "Bộ phận trách nhiệm", "owner": "Người theo dõi", "res": "Kết quả", 
        "img": "Hình ảnh", "rem": "Ghi chú", "date": "Ngày ghi", 
        "rec": "Người ghi", "export": "Xuất PDF", "save": "Lưu vào mây",
        "confirm": "Xem trước & Xác nhận", "total": "Tổng số", "sum_cat": "Thống kê phân loại"
    }
}

st.set_page_config(layout="wide", page_title="Quality Audit Tool")

# --- 3. 初始化会话状态 ---
if "records" not in st.session_state:
    st.session_state.records = []

# 选择语言
lang_choice = st.sidebar.selectbox("Language / 语言 / Ngôn ngữ", ["中文", "English", "Tiếng Việt"])
L = LANG[lang_choice]

# --- 4. 页面头部 ---
st.title(f"📄 {L['title']}")
st.subheader("📍 项目平面图 (Floor Plan)")
floor_plan = st.file_uploader("上传/更改平面图", type=['png', 'jpg', 'jpeg'])
if floor_plan:
    st.image(floor_plan, caption="Project Layout", width=400)

# --- 5. 数据录入表单 ---
with st.expander("➕ 点击录入新问题 / Add New Issue", expanded=True):
    with st.form("main_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            p_id = st.text_input(L['proj_id'])
            o_id = st.text_input(L['order_id'])
            p_name = st.text_input(L['name'])
        with c2:
            cat = st.selectbox(L['cat'], ["外观/Visual", "功能/Function", "包装/Packing", "其他/Other"])
            dept = st.text_input(L['dept'])
            owner = st.text_input(L['owner'])
        with c3:
            date_val = st.date_input(L['date'])
            recorder = st.text_input(L['rec'])
            res = st.text_input(L['res'])
        
        desc = st.text_area(L['desc'])
        img_file = st.file_uploader(L['img'], type=['jpg', 'png'])
        remark = st.text_input(L['rem'])
        
        if st.form_submit_button("添加并上传云端 (Add & Sync)"):
            new_record = {
                L['proj_id']: p_id, L['order_id']: o_id, L['name']: p_name,
                L['cat']: cat, L['desc']: desc, L['dept']: dept,
                L['owner']: owner, L['date']: str(date_val), L['rec']: recorder,
                L['res']: res, L['rem']: remark
            }
            
            # --- 步骤 1：先保存到 Google Sheets (抢救数据) ---
            try:
                df_new = pd.DataFrame([new_record])
                conn.create(data=df_new)
                st.success("✅ 数据已同步至 Google Sheets！")
                st.session_state.records.append(new_record)
            except Exception as e:
                st.error(f"❌ 写入表格失败: {e}")

# --- 6. 数据预览与 PDF 导出 ---
if st.session_state.records:
    df = pd.DataFrame(st.session_state.records)
    st.divider()
    st.subheader("📋 本次录入预览")
    st.dataframe(df)

    if st.button(f"🚀 {L['confirm']}"):
        st.warning("正在准备 PDF 报告...")
        
        # --- 步骤 2：生成 PDF (修复编码报错的关键) ---
        try:
            pdf = FPDF()
            pdf.add_page()

            # 尝试加载静态字体 (必须确保 NotoSansSC-Regular.ttf 在根目录)
            font_file = "NotoSansSC-Regular.ttf"
            try:
                pdf.add_font('MultiLang', '', font_file)
                pdf.set_font('MultiLang', size=16)
                has_font = True
            except Exception as f_err:
                st.error(f"字体加载失败，请检查文件名: {f_err}")
                pdf.set_font("Arial", size=16)
                has_font = False

            # 写入标题
            title_txt = f"{p_id} {L['title']}" if has_font else f"Quality Report: {p_id}"
            pdf.cell(200, 10, txt=title_txt, ln=True, align='C')
            
            # 写入详细内容 (取最近一条)
            pdf.set_font('MultiLang' if has_font else 'Arial', size=12)
            pdf.ln(10)
            pdf.cell(200, 10, txt=f"Project: {p_name}", ln=True)
            pdf.cell(200, 10, txt=f"Description: {desc}", ln=True)
            pdf.cell(200, 10, txt=f"Date: {datetime.now().strftime('%Y-%m-%d')}", ln=True)

            # 获取字节流
            pdf_output = pdf.output()
            
            st.download_button(
                label="📥 点击下载 PDF 报告",
                data=bytes(pdf_output),
                file_name=f"Report_{p_id}.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"⚠️ PDF 生成失败: {e}")

# --- 7. 云端全量数据查看 ---
st.divider()
st.subheader("📊 Google Sheets 云端数据实时汇总")
if st.button("刷新云端数据"):
    try:
        data = conn.read()
        st.dataframe(data)
    except Exception as e:
        st.info("无法读取云端数据，请检查 Secrets 配置。")
