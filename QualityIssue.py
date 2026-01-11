import streamlit as st
import pandas as pd
from datetime import datetime
from st_gsheets_connection import GSheetsConnection
import io

# --- 1. 初始化 ---
st.set_page_config(layout="wide", page_title="Quality Audit Tool")

# 初始化 Google Sheets 连接
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("❌ 数据库连接失败，请检查 Secrets 配置。")

# 语言字典
L = {
    "title": "品质问题记录表", 
    "proj_id": "项目ID", "name": "项目名称", 
    "cat": "问题分类", "desc": "问题描述", "owner": "跟进人", 
    "save": "🚀 提交到云端", "refresh": "🔄 刷新并查看表格"
}

st.title(f"📄 {L['title']}")

# --- 2. 数据录入表单 ---
with st.form("main_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        p_id = st.text_input(L['proj_id'])
        p_name = st.text_input(L['name'])
    with col2:
        cat = st.selectbox(L['cat'], ["外观/Visual", "功能/Function", "其他/Other"])
        owner = st.text_input(L['owner'])
    
    desc = st.text_area(L['desc'])
    submitted = st.form_submit_button(L['save'])

# --- 3. 核心提交逻辑：只存入 Google Sheets ---
if submitted:
    if not p_id or not desc:
        st.warning("⚠️ ID和描述不能为空")
    else:
        try:
            # 准备数据
            new_row = pd.DataFrame([{
                L['proj_id']: p_id,
                L['name']: p_name,
                L['cat']: cat,
                L['desc']: desc,
                L['owner']: owner,
                "记录日期": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }])
            # 写入云端
            conn.create(data=new_row)
            st.success("✅ 数据已安全同步至 Google Sheets！")
            st.balloons() # 成功特效
        except Exception as e:
            st.error(f"❌ 存入失败: {e}")

# --- 4. 数据展示与导出功能 ---
st.divider()
st.subheader("📊 已录入数据汇总")

if st.button(L['refresh']):
    # 强制不使用缓存读取最新数据
    df_all = conn.read(ttl=0)
    st.session_state['current_df'] = df_all

if 'current_df' in st.session_state:
    df_display = st.session_state['current_df']
    st.dataframe(df_display, use_container_width=True)

    # --- 导出按钮区域 ---
    st.write("📥 **选择导出格式 (Export):**")
    c1, c2 = st.columns(2)

    with c1:
        # 导出为 Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_display.to_excel(writer, index=False, sheet_name='Sheet1')
        st.download_button(
            label="💾 导出为 Excel",
            data=output.getvalue(),
            file_name=f"Quality_Report_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    with c2:
        # 导出为 PDF (简单的降级处理方案)
        if st.button("🖨️ 生成 PDF 报告"):
            try:
                from fpdf import FPDF
                pdf = FPDF()
                pdf.add_page()
                
                # 尝试加载字体，如果加载不到就不出中文，至少不报错
                font_file = "NotoSansSC-Regular.ttf"
                import os
                if os.path.exists(font_file):
                    pdf.add_font('Chinese', '', font_file)
                    pdf.set_font('Chinese', size=12)
                    pdf.cell(200, 10, txt="品质问题报告 (Quality Report)", ln=True, align='C')
                else:
                    pdf.set_font("Arial", size=12)
                    pdf.cell(200, 10, txt="Quality Issue Report (Font Missing)", ln=True, align='C')

                pdf.ln(10)
                # 只导出前5条作为预览，防止数据量太大导致排版崩溃
                for i, row in df_display.tail(5).iterrows():
                    pdf.multi_cell(0, 10, txt=f"ID: {row[L['proj_id']]} | Cat: {row[L['cat']]}")
                    pdf.multi_cell(0, 10, txt=f"Desc: {row[L['desc']]}")
                    pdf.cell(0, 5, "---" * 10, ln=True)

                pdf_bytes = pdf.output()
                st.download_button("📥 点击下载生成的 PDF", data=bytes(pdf_bytes), file_name="Report.pdf")
            except Exception as e:
                st.error(f"PDF 导出遇到一点小麻烦: {e}")
