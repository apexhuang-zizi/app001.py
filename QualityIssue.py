import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime
from st_gsheets_connection import GSheetsConnection

# --- 1. 初始化 Google Sheets 连接 ---
# 注意：secrets 必须在 Streamlit Cloud 后台配置好
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"连接配置错误，请检查 Secrets: {e}")

# --- 2. 配置多语言字典 ---
LANG = {
    "中文": {
        "title": "品质问题记录表", "proj_id": "项目ID", "name": "项目名称", 
        "cat": "问题分类", "desc": "问题描述", "owner": "跟进人", 
        "date": "记录日期", "save": "提交并同步云端", "refresh": "刷新云端数据"
    }
}
L = LANG["中文"]

st.set_page_config(layout="wide", page_title="Quality Audit Tool")

# --- 3. 数据录入表单 ---
st.title(f"📄 {L['title']}")

with st.form("main_form", clear_on_submit=True):
    c1, c2 = st.columns(2)
    with c1:
        p_id = st.text_input(L['proj_id'], key="p_id")
        p_name = st.text_input(L['name'], key="p_name")
    with c2:
        cat = st.selectbox(L['cat'], ["外观/Visual", "功能/Function", "其他/Other"])
        owner = st.text_input(L['owner'])
    
    desc = st.text_area(L['desc'])
    submitted = st.form_submit_button(L['save'])

# --- 4. 提交逻辑：核心修复 (先保存，后生成PDF) ---
if submitted:
    if not p_id or not desc:
        st.error("❌ 请填写项目ID和描述！")
    else:
        # --- 步骤 A：先保存到 Google Sheets ---
        try:
            # 准备数据
            new_data = pd.DataFrame([{
                L['proj_id']: p_id,
                L['name']: p_name,
                L['cat']: cat,
                L['desc']: desc,
                L['owner']: owner,
                L['date']: datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }])
            
            # 执行写入
            conn.create(data=new_data)
            st.success("✅ 数据已成功保存到 Google 表格！")
            
            # --- 步骤 B：尝试生成 PDF (用 try 包裹，防止它弄崩程序) ---
            try:
                pdf = FPDF()
                pdf.add_page()
                
                # 字体保险逻辑
                font_path = "NotoSansSC-Regular.ttf"
                import os
                if os.path.exists(font_path):
                    pdf.add_font('ChineseFont', '', font_path)
                    pdf.set_font('ChineseFont', size=14)
                    pdf.cell(200, 10, txt=f"项目ID: {p_id}", ln=True)
                else:
                    pdf.set_font("Arial", size=14)
                    pdf.cell(200, 10, txt=f"Project ID: {p_id} (Font missing)", ln=True)
                
                pdf.multi_cell(0, 10, txt=f"Description: {desc}")
                
                pdf_output = pdf.output()
                st.download_button(
                    label="📥 下载 PDF 报告",
                    data=bytes(pdf_output),
                    file_name=f"Report_{p_id}.pdf",
                    mime="application/pdf"
                )
            except Exception as pdf_err:
                st.warning(f"⚠️ 数据已保存，但 PDF 生成失败（可能是字体不支持）: {pdf_err}")

        except Exception as e:
            st.error(f"❌ 写入表格失败，请检查权限或列名: {e}")

# --- 5. 查看云端数据 ---
st.divider()
if st.button(L['refresh']):
    try:
        # 强制清除缓存读取最新数据
        df_all = conn.read(ttl=0) 
        st.subheader("📊 云端全量数据")
        st.dataframe(df_all)
    except Exception as e:
        st.error(f"读取失败: {e}")
