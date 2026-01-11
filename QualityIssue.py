import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import os
import sys
import subprocess

# --- 1. 自动环境检查 (解决 ModuleNotFoundError) ---
try:
    from st_gsheets_connection import GSheetsConnection
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "st-gsheets-connection"])
    from st_gsheets_connection import GSheetsConnection

# --- 2. 页面与连接配置 ---
st.set_page_config(layout="wide", page_title="Quality Audit Tool")

# 初始化 Google Sheets 连接
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"❌ 数据库连接初始化失败，请检查 Secrets 配置: {e}")

# 多语言设置
LANG = {
    "中文": {
        "title": "品质问题记录表", "proj_id": "项目ID", "name": "项目名称", 
        "cat": "问题分类", "desc": "问题描述", "owner": "跟进人", 
        "date": "记录日期", "save": "提交并上传云端", "refresh": "刷新云端数据"
    }
}
L = LANG["中文"]

st.title(f"📄 {L['title']}")

# --- 3. 数据录入表单 ---
with st.form("main_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        p_id = st.text_input(L['proj_id'])
        p_name = st.text_input(L['name'])
    with col2:
        cat = st.selectbox(L['cat'], ["外观/Visual", "功能/Function", "包装/Packing", "其他/Other"])
        owner = st.text_input(L['owner'])
    
    desc = st.text_area(L['desc'])
    submitted = st.form_submit_button(L['save'])

# --- 4. 提交逻辑：先存数据，再试 PDF ---
if submitted:
    if not p_id or not desc:
        st.warning("⚠️ 请至少填写项目ID和问题描述。")
    else:
        # --- 步骤 A：先保存到 Google Sheets (确保数据安全) ---
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            new_row = pd.DataFrame([{
                L['proj_id']: p_id,
                L['name']: p_name,
                L['cat']: cat,
                L['desc']: desc,
                L['owner']: owner,
                L['date']: timestamp
            }])
            
            # 写入云端表格
            conn.create(data=new_row)
            st.success("✅ 数据已成功保存到 Google Sheets！")
            
            # --- 步骤 B：尝试生成 PDF (修复 Unicode/latin-1 报错) ---
            try:
                # 必须确保使用的是 fpdf2 库
                pdf = FPDF()
                pdf.add_page()
                
                # 字体加载逻辑
                font_path = "NotoSansSC-Regular.ttf" # 请确保 GitHub 根目录有此文件
                
                if os.path.exists(font_path):
                    pdf.add_font('ChineseFont', '', font_path)
                    pdf.set_font('ChineseFont', size=16)
                    
                    # 写入中文内容 (fpdf2 自动处理 UTF-8，禁止再加 .encode('latin-1'))
                    pdf.cell(200, 10, txt=f"品质记录: {p_id}", ln=True, align='C')
                    pdf.set_font('ChineseFont', size=12)
                    pdf.ln(10)
                    pdf.cell(200, 10, txt=f"项目名称: {p_name}", ln=True)
                    pdf.multi_cell(0, 10, txt=f"问题描述: {desc}")
                else:
                    # 降级方案：未找到字体时显示英文，防止崩溃
                    pdf.set_font("Arial", size=16)
                    pdf.cell(200, 10, txt=f"Quality Report: {p_id}", ln=True, align='C')
                    st.info("ℹ️ 未检测到中文字体文件，PDF 将以英文显示。")

                pdf.cell(200, 10, txt=f"Date: {timestamp}", ln=True)

                # 生成 PDF 字节流
                pdf_output = pdf.output()
                
                st.download_button(
                    label="📥 下载 PDF 报告",
                    data=bytes(pdf_output),
                    file_name=f"Report_{p_id}.pdf",
                    mime="application/pdf"
                )
            except Exception as pdf_err:
                # 即使 PDF 失败，也不会影响上面已经成功的 Google Sheets 保存
                st.warning(f"⚠️ 数据已保存，但 PDF 生成失败: {pdf_err}")

        except Exception as sheet_err:
            st.error(f"❌ 写入 Google Sheets 失败: {sheet_err}")

# --- 5. 实时汇总展示 ---
st.divider()
if st.button(L['refresh']):
    try:
        # ttl=0 强制跳过缓存，读取最新录入的数据
        df_all = conn.read(ttl=0)
        st.subheader("📊 云端全量数据明细")
        st.dataframe(df_all, use_container_width=True)
    except Exception as e:
        st.info("当前云端无数据，或者连接尚未配置成功。")
