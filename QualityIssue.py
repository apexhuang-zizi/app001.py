import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime
from PIL import Image
import io

# --- 1. 配置与多语言字典 ---
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

# --- 2. 初始化数据存储 (Session State) ---
if "records" not in st.session_state:
    st.session_state.records = []
if "cloud_data" not in st.session_state:
    st.session_state.cloud_data = []

# 选择语言
lang_choice = st.sidebar.selectbox("Language / 语言 / Ngôn ngữ", ["中文", "English", "Tiếng Việt"])
L = LANG[lang_choice]

# --- 3. 页面头部 & 平面图 ---
st.title(f"📄 {L['title']}")
st.subheader("📍 项目平面图 (Floor Plan)")
floor_plan = st.file_uploader("上传/更改平面图", type=['png', 'jpg', 'jpeg'])
if floor_plan:
    st.image(floor_plan, caption="Project Layout", width=400)

# --- 4. 数据录入表单 ---
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
        
        if st.form_submit_button("添加记录 (Add to List)"):
            new_data = {
                L['proj_id']: p_id, L['order_id']: o_id, L['name']: p_name,
                L['cat']: cat, L['desc']: desc, L['dept']: dept,
                L['owner']: owner, L['date']: str(date_val), L['rec']: recorder,
                L['res']: res, L['rem']: remark, "img_raw": img_file
            }
            st.session_state.records.append(new_data)
            st.success("Record added!")

# --- 5. 数据预览与汇总 ---
if st.session_state.records:
    df = pd.DataFrame(st.session_state.records)
    st.divider()
    st.subheader("📋 问题清单预览")
    # 显示图片预览
    st.write("---")
    for i, row in df.iterrows():
        cols = st.columns([1, 4, 2])
        with cols[0]:
            if row["img_raw"]:
                st.image(row["img_raw"], width=100)
        with cols[1]:
            st.write(f"**{row[L['proj_id']]} - {row[L['cat']]}**")
            st.write(f"描述: {row[L['desc']]}")
        with cols[2]:
            st.write(f"跟进人: {row[L['owner']]}")
    
    # 汇总统计
    st.info(f"📊 {L['total']}: {len(df)} | {L['sum_cat']}: {df[L['cat']].value_counts().to_dict()}")

    # --- 6. 导出预览与确认弹窗 ---
    st.write("---")
    if st.button(f"🚀 {L['confirm']}"):
        st.warning("即将生成PDF报告，请确认以下信息：")
        st.table(df.drop(columns=["img_raw"])) # 预览文字部分
        
        col_btn1, col_btn2 = st.columns(2)
        
    # 确认导出
        with col_btn1:
            # 1. 导入和初始化 (注意：所有的行现在都整齐地对齐了)
            from fpdf import FPDF
            pdf = FPDF()
            pdf.add_page()

            # 2. 注册并使用字体 (确保 NotoSansSC-Regular.ttf 文件在 GitHub 根目录)
            try:
                pdf.add_font('MultiLang', '', 'NotoSansSC-Regular.ttf', uni=True)
                pdf.set_font('MultiLang', size=12)
            except:
                # 如果字体没找到，暂时回退到 Arial 避免崩溃
                pdf.set_font("Arial", size=12)

            # 3. 写入内容
            pdf.cell(200, 10, txt=f"{p_id} {L['title']}", ln=True, align='C')
            pdf.cell(200, 10, txt=f"Date: {datetime.now().strftime('%Y-%m-%d')}", ln=True)
            
            # 4. 生成并提供下载
            # 修改为这个写法：
            pdf_output = pdf.output()  # fpdf2 默认直接输出字节数组(bytearray)
                 st.download_button(
            label="✅ 确认生成并下载 PDF",
            data=bytes(pdf_output), # 将其转换为字节
            file_name=f"{p_id}_Report.pdf",
            mime="application/pdf"
            ) 
            st.download_button(
                label="✅ 确认生成并下载 PDF",
                data=pdf_output,
                file_name=f"{p_id}_Report.pdf",
                mime="application/pdf"
            )

        # 取消并保存
        with col_btn2:
            if st.button("❌ 取消并保存到云端"):
                st.session_state.cloud_data.extend(st.session_state.records)
                st.session_state.records = []
                st.success("已安全保存到云端数据库！")
        # 在 app.py 的末尾添加
        st.divider() # 画一条分割线
        st.subheader("📊 已录入数据汇总")
        # 从 Google Sheets 获取所有数据并显示
        data = conn.read(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"])
        st.dataframe(data)
