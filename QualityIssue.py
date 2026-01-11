import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime
from st_gsheets_connection import GSheetsConnection
import sys
import subprocess

# --- 0. 自动修复环境 (防止 ModuleNotFoundError) ---
try:
    from st_gsheets_connection import GSheetsConnection
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "st-gsheets-connection"])
    from st_gsheets_connection import GSheetsConnection

# --- 1. 初始化页面配置 ---
st.set_page_config(layout="wide", page_title="Quality Audit Tool")

# --- 2. 初始化 Google Sheets 连接 ---
# 请确保已经在 Streamlit Cloud 的 Secrets 中配置了 connections.gsheets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"❌ 无法连接到 Google Sheets，请检查 Secrets 配置: {e}")

# --- 3. 多语言字典 ---
LANG = {
    "中文": {
        "title": "品质问题记录表", "proj_id": "项目ID", "name": "项目名称", 
        "cat": "问题分类", "desc": "问题描述", "owner": "跟进人", 
        "date": "记录日期", "save": "提交并同步云端", "refresh": "刷新云端汇总"
    }
}
L = LANG["中文"]

st.title(f"📄 {L['title']}")

# --- 4. 数据录入表单 ---
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

# --- 5. 核心逻辑：先存数据，后做 PDF ---
if submitted:
    if not p_id or not desc:
        st.warning("⚠️ 请至少填写项目ID和问题描述。")
    else:
        # 第一步：保存数据到 Google Sheets (优先级最高)
        try:
            # 构造要存入的数据
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
            # 注意：如果表格为空，conn.create 会自动创建列名
            conn.create(data=new_row)
            st.success("✅ 数据已成功保存到 Google Sheets！")
            
            # --- 第二步：尝试生成 PDF (放在独立的 try 中，报错也不会影响上面的保存结果) ---
            try:
                # 使用 fpdf2 (支持 Unicode)
                pdf = FPDF()
                pdf.add_page()
                
                # 字体加载逻辑：必须确保 NotoSansSC-Regular.ttf 在根目录
                import os
                font_path = "NotoSansSC-Regular.ttf"
                
                if os.path.exists(font_path):
                    pdf.add_font('ChineseFont', '', font_path)
                    pdf.set_font('ChineseFont', size=16)
                    can_use_chinese = True
                else:
                    pdf.set_font("Arial", size=16)
                    can_use_chinese = False
                    st.info("ℹ️ 未在根目录找到 NotoSansSC-Regular.ttf，PDF将显示英文。")

                # 写入 PDF 内容
                if can_use_chinese:
                    pdf.cell(200, 10, txt=f"【品质记录】 {p_id}", ln=True, align='C')
                    pdf.set_font('ChineseFont', size=12)
                    pdf.ln(10)
                    pdf.cell(200, 10, txt=f"项目名称: {p_name}", ln=True)
                    pdf.multi_cell(0, 10, txt=f"问题描述: {desc}")
                else:
                    pdf.cell(200, 10, txt=f"Quality Report: {p_id}", ln=True, align='C')
                    pdf.ln(10)
                    pdf.cell(200, 10, txt=f"Project: {p_name}", ln=True)
                    pdf.multi_cell(0, 10, txt=f"Description: {desc}")
                
                pdf.cell(200, 10, txt=f"Date: {timestamp}", ln=True)

                # 生成字节流 (fpdf2 自动处理 UTF-8，不要加 .encode('latin-1'))
                pdf_output = pdf.output()
                
                st.download_button(
                    label="📥 下载 PDF 报告",
                    data=bytes(pdf_output),
                    file_name=f"Report_{p_id}.pdf",
                    mime="application/pdf"
                )
            except Exception as pdf_err:
                st.error(f"⚠️ PDF 生成失败（但不影响数据保存）: {pdf_err}")

        except Exception as sheet_err:
            st.error(f"❌ 无法保存数据到 Google Sheets: {sheet_err}")

# --- 6. 底部数据展示与刷新 ---
st.divider()
if st.button(L['refresh']):
    try:
        # ttl=0 确保每次点击都拉取最新数据而非缓存
        all_data = conn.read(ttl=0)
        st.subheader("📊 云端全量数据明细")
        st.dataframe(all_data, use_container_width=True)
    except Exception as e:
        st.info("暂无数据或连接失败，请确认表格是否有内容且 Secrets 正确。")
