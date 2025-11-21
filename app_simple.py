"""
简化版 Gradio 界面 - 测试用
"""
import gradio as gr

def test_function(text):
    return f"您输入了：{text}", f"这是回复：{text}"

with gr.Blocks() as demo:
    gr.Markdown("# 测试界面")
    
    with gr.Row():
        input_box = gr.Textbox(label="输入")
        submit = gr.Button("提交")
    
    with gr.Row():
        output1 = gr.Textbox(label="输出1")
        output2 = gr.Textbox(label="输出2")
    
    submit.click(test_function, inputs=[input_box], outputs=[output1, output2])

if __name__ == "__main__":
    demo.launch()
