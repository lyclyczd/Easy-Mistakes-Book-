import sqlite3
import os
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, scrolledtext

class MistakeBook:
    def __init__(self):
        # 数据库文件路径
        self.db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mistakes.db")
        self.conn = None
        self.cursor = None
        self.setup_database()
        
    def setup_database(self):
        """创建数据库和表结构"""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        
        # 创建错题表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS mistakes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                question TEXT NOT NULL,
                question_type TEXT NOT NULL,  -- 题目类型：单选、多选、填空、解答等
                options TEXT,  -- 选择题的选项，JSON格式
                wrong_answer TEXT,
                correct_answer TEXT NOT NULL,
                explanation TEXT,  -- 题目解析
                tags TEXT,
                difficulty INTEGER DEFAULT 3,  -- 难度等级1-5
                add_date TEXT NOT NULL,
                last_review TEXT,
                review_count INTEGER DEFAULT 0,
                correct_count INTEGER DEFAULT 0
            )
        ''')
        
        # 创建复习记录表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mistake_id INTEGER NOT NULL,
                review_date TEXT NOT NULL,
                result BOOLEAN NOT NULL,
                user_answer TEXT,  -- 用户作答的答案
                FOREIGN KEY (mistake_id) REFERENCES mistakes(id)
            )
        ''')
        self.conn.commit()
    
    def add_mistake(self, subject, question_type, question, options, correct_answer, 
                   explanation="", tags="", difficulty=3, wrong_answer=""):
        """添加新的错题"""
        add_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 处理选项格式
        if options and isinstance(options, list):
            options = str(options)  # 将选项列表转为字符串
        
        self.cursor.execute('''
            INSERT INTO mistakes (
                subject, question_type, question, options, wrong_answer, 
                correct_answer, explanation, tags, difficulty, add_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (subject, question_type, question, options, wrong_answer, 
              correct_answer, explanation, tags, difficulty, add_date))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def update_mistake(self, mistake_id, subject, question_type, question, options, 
                      correct_answer, explanation, tags, difficulty, wrong_answer):
        """更新错题信息"""
        # 处理选项格式
        if options and isinstance(options, list):
            options = str(options)  # 将选项列表转为字符串
            
        self.cursor.execute('''
            UPDATE mistakes
            SET subject=?, question_type=?, question=?, options=?, wrong_answer=?, 
                correct_answer=?, explanation=?, tags=?, difficulty=?
            WHERE id=?
        ''', (subject, question_type, question, options, wrong_answer, 
              correct_answer, explanation, tags, difficulty, mistake_id))
        self.conn.commit()
    
    def delete_mistake(self, mistake_id):
        """删除错题"""
        self.cursor.execute('DELETE FROM mistakes WHERE id=?', (mistake_id,))
        self.cursor.execute('DELETE FROM reviews WHERE mistake_id=?', (mistake_id,))
        self.conn.commit()
    
    def add_review(self, mistake_id, result, user_answer):
        """添加复习记录并更新错题统计"""
        review_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute('''
            INSERT INTO reviews (mistake_id, review_date, result, user_answer)
            VALUES (?, ?, ?, ?)
        ''', (mistake_id, review_date, result, user_answer))
        
        # 更新错题的复习统计
        self.cursor.execute('''
            UPDATE mistakes
            SET last_review=?, review_count=review_count+1, 
                correct_count=correct_count+?
            WHERE id=?
        ''', (review_date, 1 if result else 0, mistake_id))
        self.conn.commit()
    
    def get_mistakes(self, subject=None, tag=None, question_type=None, difficulty=None):
        """获取错题列表，支持多种筛选条件"""
        query = "SELECT * FROM mistakes"
        conditions = []
        params = []
        
        if subject:
            conditions.append("subject=?")
            params.append(subject)
        if tag:
            conditions.append("tags LIKE ?")
            params.append(f"%{tag}%")
        if question_type:
            conditions.append("question_type=?")
            params.append(question_type)
        if difficulty:
            conditions.append("difficulty=?")
            params.append(difficulty)
            
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY last_review ASC, add_date DESC"  # 优先显示未复习或复习时间早的题目
        self.cursor.execute(query, tuple(params))
        return self.cursor.fetchall()
    
    def get_mistake_by_id(self, mistake_id):
        """根据ID获取错题详情"""
        self.cursor.execute('SELECT * FROM mistakes WHERE id=?', (mistake_id,))
        return self.cursor.fetchone()
    
    def get_reviews(self, mistake_id):
        """获取某错题的复习记录"""
        self.cursor.execute('SELECT * FROM reviews WHERE mistake_id=? ORDER BY review_date DESC', (mistake_id,))
        return self.cursor.fetchall()
    
    def get_subjects(self):
        """获取所有科目列表"""
        self.cursor.execute('SELECT DISTINCT subject FROM mistakes ORDER BY subject')
        return [row[0] for row in self.cursor.fetchall()]
    
    def get_question_types(self):
        """获取所有题目类型列表"""
        types = ["单选", "多选", "填空", "判断", "解答"]
        return types
    
    def get_tags(self):
        """获取所有标签列表"""
        self.cursor.execute('SELECT tags FROM mistakes')
        tags = set()
        for row in self.cursor.fetchall():
            if row[0]:
                for tag in row[0].split(','):
                    tags.add(tag.strip())
        return sorted(tags)
    
    def get_difficulties(self):
        """获取难度等级列表"""
        return [1, 2, 3, 4, 5]
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()


class MistakeBookGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Python电子错题本（含在线作答）")
        self.root.geometry("1100x800")
        
        # 创建错题本实例
        self.mistake_book = MistakeBook()
        self.current_mistake_id = None
        self.current_question_type = None
        
        # 创建界面
        self.create_widgets()
        
        # 加载数据
        self.load_mistakes()
        
        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def create_widgets(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建筛选面板
        filter_frame = ttk.LabelFrame(main_frame, text="筛选条件")
        filter_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 科目选择
        ttk.Label(filter_frame, text="科目:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.subject_var = tk.StringVar()
        self.subject_combo = ttk.Combobox(filter_frame, textvariable=self.subject_var)
        self.subject_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        self.subject_combo['values'] = [''] + self.mistake_book.get_subjects()
        self.subject_combo.bind("<<ComboboxSelected>>", self.load_mistakes)
        
        # 题目类型选择
        ttk.Label(filter_frame, text="类型:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.type_var = tk.StringVar()
        self.type_combo = ttk.Combobox(filter_frame, textvariable=self.type_var)
        self.type_combo.grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
        self.type_combo['values'] = [''] + self.mistake_book.get_question_types()
        self.type_combo.bind("<<ComboboxSelected>>", self.load_mistakes)
        
        # 难度选择
        ttk.Label(filter_frame, text="难度:").grid(row=0, column=4, padx=5, pady=5, sticky=tk.W)
        self.difficulty_var = tk.StringVar()
        self.difficulty_combo = ttk.Combobox(filter_frame, textvariable=self.difficulty_var)
        self.difficulty_combo.grid(row=0, column=5, padx=5, pady=5, sticky=tk.W)
        self.difficulty_combo['values'] = [''] + [str(d) for d in self.mistake_book.get_difficulties()]
        self.difficulty_combo.bind("<<ComboboxSelected>>", self.load_mistakes)
        
        # 标签选择
        ttk.Label(filter_frame, text="标签:").grid(row=0, column=6, padx=5, pady=5, sticky=tk.W)
        self.tag_var = tk.StringVar()
        self.tag_combo = ttk.Combobox(filter_frame, textvariable=self.tag_var)
        self.tag_combo.grid(row=0, column=7, padx=5, pady=5, sticky=tk.W)
        self.tag_combo['values'] = [''] + self.mistake_book.get_tags()
        self.tag_combo.bind("<<ComboboxSelected>>", self.load_mistakes)
        
        # 刷新按钮
        ttk.Button(filter_frame, text="刷新", command=self.load_mistakes).grid(
            row=0, column=8, padx=5, pady=5
        )
        
        # 添加错题按钮
        ttk.Button(filter_frame, text="添加错题", command=self.add_mistake).grid(
            row=0, column=9, padx=5, pady=5
        )
        
        # 创建主内容区
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 创建错题列表框架（左侧）
        list_frame = ttk.LabelFrame(content_frame, text="错题列表")
        list_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        list_frame.config(width=500)
        
        # 错题列表
        columns = ("id", "subject", "type", "question", "diff", "reviews")
        self.mistake_tree = ttk.Treeview(
            list_frame, columns=columns, show="headings", selectmode="browse"
        )
        
        # 设置列宽和标题
        self.mistake_tree.column("id", width=40, anchor=tk.CENTER)
        self.mistake_tree.column("subject", width=80, anchor=tk.W)
        self.mistake_tree.column("type", width=50, anchor=tk.CENTER)
        self.mistake_tree.column("question", width=270, anchor=tk.W)
        self.mistake_tree.column("diff", width=50, anchor=tk.CENTER)
        self.mistake_tree.column("reviews", width=50, anchor=tk.CENTER)
        
        self.mistake_tree.heading("id", text="ID")
        self.mistake_tree.heading("subject", text="科目")
        self.mistake_tree.heading("type", text="类型")
        self.mistake_tree.heading("question", text="题目")
        self.mistake_tree.heading("diff", text="难度")
        self.mistake_tree.heading("reviews", text="复习")
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.mistake_tree.yview)
        self.mistake_tree.configure(yscroll=scrollbar.set)
        
        # 布局
        self.mistake_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 绑定选择事件
        self.mistake_tree.bind("<<TreeviewSelect>>", self.show_mistake_details)
        
        # 创建错题详情和作答区（右侧）
        detail_frame = ttk.LabelFrame(content_frame, text="错题详情与作答")
        detail_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # 创建详情标签页
        self.detail_notebook = ttk.Notebook(detail_frame)
        self.detail_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 详情标签
        info_tab = ttk.Frame(self.detail_notebook)
        self.detail_notebook.add(info_tab, text="详情")
        
        # 作答标签
        answer_tab = ttk.Frame(self.detail_notebook)
        self.detail_notebook.add(answer_tab, text="作答")
        
        # 统计标签
        stats_tab = ttk.Frame(self.detail_notebook)
        self.detail_notebook.add(stats_tab, text="统计")
        
        # 初始化各个标签页内容
        self.init_info_tab(info_tab)
        self.init_answer_tab(answer_tab)
        self.init_stats_tab(stats_tab)
        
        # 默认显示详情标签页
        self.detail_notebook.select(0)
    
    def init_info_tab(self, parent):
        """初始化详情标签页内容"""
        # 详情内容
        detail_frame = ttk.Frame(parent)
        detail_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 详情文本
        self.info_text = scrolledtext.ScrolledText(detail_frame, wrap=tk.WORD)
        self.info_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.info_text.config(state=tk.DISABLED)
        
        # 操作按钮
        button_frame = ttk.Frame(detail_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(button_frame, text="编辑", command=self.edit_mistake).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="删除", command=self.delete_mistake).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="去练习", command=lambda: self.detail_notebook.select(1)).pack(side=tk.LEFT, padx=5)
    
    def init_answer_tab(self, parent):
        """初始化作答标签页内容"""
        # 作答区框架
        answer_frame = ttk.Frame(parent)
        answer_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 题目显示区域
        self.question_frame = ttk.LabelFrame(answer_frame, text="题目")
        self.question_frame.pack(fill=tk.X, pady=5)
        
        # 题目类型标签
        self.type_label = ttk.Label(self.question_frame, text="", font=("Arial", 10, "bold"))
        self.type_label.pack(anchor=tk.W, padx=5, pady=2)
        
        # 题目内容
        self.question_text = tk.Text(self.question_frame, height=6, wrap=tk.WORD)
        self.question_text.pack(fill=tk.X, padx=5, pady=5)
        self.question_text.config(state=tk.DISABLED)
        
        # 选项区域（单选、多选使用）
        self.options_frame = ttk.Frame(answer_frame)
        self.options_frame.pack(fill=tk.X, pady=5)
        self.option_vars = {}  # 存储选项变量
        self.option_buttons = {}  # 存储选项按钮
        
        # 答案输入区域（填空、解答等使用）
        self.answer_frame = ttk.LabelFrame(answer_frame, text="作答区")
        self.answer_frame.pack(fill=tk.X, pady=5)
        
        self.answer_entry = scrolledtext.ScrolledText(self.answer_frame, height=5, wrap=tk.WORD)
        self.answer_entry.pack(fill=tk.BOTH, padx=5, pady=5, expand=True)
        
        # 底部按钮
        button_frame = ttk.Frame(answer_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="提交答案", command=self.submit_answer).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="显示答案", command=self.show_correct_answer).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="重新作答", command=self.reset_answer).pack(side=tk.LEFT, padx=5)
    
    def init_stats_tab(self, parent):
        """初始化统计标签页内容"""
        # 统计信息框架
        stats_frame = ttk.Frame(parent)
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 整体统计
        summary_frame = ttk.LabelFrame(stats_frame, text="整体统计")
        summary_frame.pack(fill=tk.X, pady=5)
        
        self.summary_text = tk.Text(summary_frame, height=5, wrap=tk.WORD)
        self.summary_text.pack(fill=tk.X, padx=5, pady=5)
        self.summary_text.config(state=tk.DISABLED)
        
        # 复习记录
        review_frame = ttk.LabelFrame(stats_frame, text="复习记录")
        review_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 复习记录列表
        columns = ("date", "result", "answer")
        self.review_tree = ttk.Treeview(
            review_frame, columns=columns, show="headings", selectmode="browse"
        )
        
        # 设置列宽和标题
        self.review_tree.column("date", width=150, anchor=tk.W)
        self.review_tree.column("result", width=50, anchor=tk.CENTER)
        self.review_tree.column("answer", width=300, anchor=tk.W)
        
        self.review_tree.heading("date", text="日期")
        self.review_tree.heading("result", text="结果")
        self.review_tree.heading("answer", text="你的答案")
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(review_frame, orient=tk.VERTICAL, command=self.review_tree.yview)
        self.review_tree.configure(yscroll=scrollbar.set)
        
        # 布局
        self.review_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def load_mistakes(self, event=None):
        """加载错题列表"""
        # 清空当前列表
        for item in self.mistake_tree.get_children():
            self.mistake_tree.delete(item)
        
        # 获取筛选条件
        subject = self.subject_var.get() if self.subject_var.get() != "" else None
        tag = self.tag_var.get() if self.tag_var.get() != "" else None
        q_type = self.type_var.get() if self.type_var.get() != "" else None
        difficulty = self.difficulty_var.get() if self.difficulty_var.get() != "" else None
        
        # 获取错题数据
        mistakes = self.mistake_book.get_mistakes(subject, tag, q_type, difficulty)
        
        # 添加到列表
        for mistake in mistakes:
            # 计算复习进度百分比
            reviews = mistake[12]  # review_count
            correct = mistake[13]  # correct_count
            progress = f"{correct}/{reviews}" if reviews > 0 else "未复习"
            
            self.mistake_tree.insert("", tk.END, values=(
                mistake[0],  # id
                mistake[1],  # subject
                mistake[2],  # question_type
                mistake[3][:50] + "..." if len(mistake[3]) > 50 else mistake[3],  # question
                mistake[9],  # difficulty
                progress
            ))
        
        # 更新筛选条件的选项列表
        self.subject_combo['values'] = [''] + self.mistake_book.get_subjects()
        self.tag_combo['values'] = [''] + self.mistake_book.get_tags()
    
    def show_mistake_details(self, event):
        """显示选中的错题详情"""
        selection = self.mistake_tree.selection()
        if not selection:
            return
        
        item = self.mistake_tree.item(selection[0])
        mistake_id = item['values'][0]
        self.current_mistake_id = mistake_id
        mistake = self.mistake_book.get_mistake_by_id(mistake_id)
        
        if mistake:
            self.current_question_type = mistake[2]  # 保存题目类型
            
            # 构建详情文本
            detail = f"科目: {mistake[1]}\n"
            detail += f"类型: {mistake[2]}\n"
            detail += f"难度: {mistake[9]}星\n"
            detail += f"添加时间: {mistake[10]}\n"
            detail += f"最后复习: {mistake[11] if mistake[11] else '未复习'}\n"
            detail += f"复习次数: {mistake[12]} (正确: {mistake[13]})\n"
            detail += f"标签: {mistake[8] if mistake[8] else '无'}\n\n"
            detail += f"题目:\n{mistake[3]}\n\n"
            
            # 显示选项（如果是选择题）
            if mistake[2] in ["单选", "多选"] and mistake[4]:
                try:
                    options = eval(mistake[4])  # 将字符串转回列表
                    detail += "选项:\n"
                    for key, value in options.items():
                        detail += f"{key}. {value}\n"
                    detail += "\n"
                except:
                    pass
                    
            detail += f"错误答案:\n{mistake[5] if mistake[5] else '无记录'}\n\n"
            detail += f"正确答案:\n{mistake[6]}\n\n"
            detail += f"解析:\n{mistake[7] if mistake[7] else '无记录'}\n\n"
            
            # 更新详情文本
            self.info_text.config(state=tk.NORMAL)
            self.info_text.delete(1.0, tk.END)
            self.info_text.insert(tk.END, detail)
            self.info_text.config(state=tk.DISABLED)
            
            # 更新作答区域
            self.update_answer_tab(mistake)
            
            # 更新统计区域
            self.update_stats_tab(mistake)
    
    def update_answer_tab(self, mistake):
        """更新作答区域的内容"""
        # 重置作答区
        self.answer_entry.delete("1.0", tk.END)
        
        # 清空选项区域
        for widget in self.options_frame.winfo_children():
            widget.destroy()
        self.option_vars = {}
        self.option_buttons = {}
        
        # 清空问题区域
        self.question_text.config(state=tk.NORMAL)
        self.question_text.delete("1.0", tk.END)
        self.question_text.insert(tk.END, mistake[3])
        self.question_text.config(state=tk.DISABLED)
        
        # 更新题目类型标签
        self.type_label.config(text=f"题型: {mistake[2]}")
        
        # 根据题目类型设置作答区域
        if mistake[2] in ["单选", "多选"]:
            # 显示选项
            if mistake[4]:
                try:
                    options = eval(mistake[4])  # 将字符串转回列表
                    
                    if mistake[2] == "单选":
                        # 单选按钮
                        var = tk.StringVar()
                        for key, value in options.items():
                            rb = ttk.Radiobutton(
                                self.options_frame, 
                                text=f"{key}. {value}",
                                variable=var,
                                value=key
                            )
                            rb.pack(anchor=tk.W, padx=5, pady=2)
                            self.option_buttons[key] = rb
                        self.option_vars["单选"] = var
                        
                    else:  # 多选
                        for key, value in options.items():
                            var = tk.BooleanVar()
                            cb = ttk.Checkbutton(
                                self.options_frame,
                                text=f"{key}. {value}",
                                variable=var
                            )
                            cb.pack(anchor=tk.W, padx=5, pady=2)
                            self.option_vars[key] = var
                            self.option_buttons[key] = cb
                    
                    # 隐藏文本作答区
                    self.answer_frame.pack_forget()
                    
                except:
                    # 如果解析选项失败，显示文本作答区
                    self.options_frame.pack_forget()
                    self.answer_frame.pack(fill=tk.X, pady=5)
            else:
                # 没有选项数据，显示文本作答区
                self.options_frame.pack_forget()
                self.answer_frame.pack(fill=tk.X, pady=5)
        
        else:
            # 对于填空、判断、解答题，直接显示文本作答区
            self.options_frame.pack_forget()
            self.answer_frame.pack(fill=tk.X, pady=5)
    
    def update_stats_tab(self, mistake):
        """更新统计区域的内容"""
        # 更新整体统计信息
        self.summary_text.config(state=tk.NORMAL)
        self.summary_text.delete("1.0", tk.END)
        
        stats = f"科目: {mistake[1]}\n"
        stats += f"题型: {mistake[2]}\n"
        stats += f"难度: {mistake[9]}星\n\n"
        stats += f"复习次数: {mistake[12]}\n"
        stats += f"正确次数: {mistake[13]}\n"
        stats += f"正确率: {int(mistake[13]/mistake[12]*100) if mistake[12] > 0 else 0}%\n"
        stats += f"最后一次复习: {mistake[11] if mistake[11] else '从未'}\n"
        
        self.summary_text.insert(tk.END, stats)
        self.summary_text.config(state=tk.DISABLED)
        
        # 更新复习记录列表
        for item in self.review_tree.get_children():
            self.review_tree.delete(item)
        
        reviews = self.mistake_book.get_reviews(mistake[0])
        for review in reviews:
            result = "✓" if review[3] else "✗"
            self.review_tree.insert("", tk.END, values=(
                review[2],  # 日期
                result,
                review[4] if review[4] else "无记录"  # 用户答案
            ))
    
    def submit_answer(self):
        """提交答案并检查"""
        if not self.current_mistake_id:
            messagebox.showinfo("提示", "请先选择一个错题")
            return
            
        mistake = self.mistake_book.get_mistake_by_id(self.current_mistake_id)
        if not mistake:
            return
            
        # 获取用户答案
        user_answer = ""
        
        if self.current_question_type == "单选":
            if "单选" in self.option_vars:
                user_answer = self.option_vars["单选"].get()
        elif self.current_question_type == "多选":
            selected = []
            for key, var in self.option_vars.items():
                if var.get():
                    selected.append(key)
            user_answer = ",".join(selected)
        else:  # 填空、判断、解答题
            user_answer = self.answer_entry.get("1.0", tk.END).strip()
        
        if not user_answer:
            messagebox.showinfo("提示", "请输入答案")
            return
            
        # 判断答案是否正确
        if self.current_question_type == "判断":
            # 对于判断题，不区分大小写和空格
            result = (user_answer.lower().replace(" ", "") == mistake[6].lower().replace(" ", ""))
        else:
            # 对于其他题目，直接比较字符串（在实际应用中可能需要更复杂的比较逻辑）
            result = (user_answer == mistake[6])
        
        # 保存复习记录
        self.mistake_book.add_review(self.current_mistake_id, result, user_answer)
        
        # 显示结果
        if result:
            messagebox.showinfo("结果", "回答正确！")
        else:
            messagebox.showinfo("结果", "回答错误！\n正确答案: " + mistake[6])
        
        # 重新加载当前错题详情
        self.show_mistake_details(None)
    
    def show_correct_answer(self):
        """显示正确答案"""
        if not self.current_mistake_id:
            return
            
        mistake = self.mistake_book.get_mistake_by_id(self.current_mistake_id)
        if mistake:
            messagebox.showinfo("正确答案", mistake[6])
    
    def reset_answer(self):
        """重置作答区域"""
        # 清空作答区域
        self.answer_entry.delete("1.0", tk.END)
        
        # 重置选项选择
        for var in self.option_vars.values():
            if isinstance(var, tk.StringVar):
                var.set("")
            elif isinstance(var, tk.BooleanVar):
                var.set(False)
    
    def add_mistake(self):
        """添加新错题"""
        dialog = AddEditMistakeDialog(self.root, self.mistake_book)
        self.root.wait_window(dialog.top)
        self.load_mistakes()
    
    def edit_mistake(self):
        """编辑错题"""
        if not self.current_mistake_id:
            messagebox.showinfo("提示", "请先选择一个错题")
            return
        
        mistake = self.mistake_book.get_mistake_by_id(self.current_mistake_id)
        if not mistake:
            return
            
        # 处理选项数据
        options = None
        if mistake[4]:
            try:
                options = eval(mistake[4])
            except:
                options = mistake[4]
        
        dialog = AddEditMistakeDialog(
            self.root, self.mistake_book, 
            mistake_id=mistake[0],
            subject=mistake[1],
            question_type=mistake[2],
            question=mistake[3],
            options=options,
            wrong_answer=mistake[5],
            correct_answer=mistake[6],
            explanation=mistake[7],
            tags=mistake[8],
            difficulty=mistake[9]
        )
        self.root.wait_window(dialog.top)
        self.load_mistakes()
        self.show_mistake_details(None)
    
    def delete_mistake(self):
        """删除错题"""
        if not self.current_mistake_id:
            messagebox.showinfo("提示", "请先选择一个错题")
            return
        
        if not messagebox.askyesno("确认", "确定要删除这个错题吗？"):
            return
        
        self.mistake_book.delete_mistake(self.current_mistake_id)
        self.load_mistakes()
        self.current_mistake_id = None
        
        # 清空详情和作答区
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete(1.0, tk.END)
        self.info_text.config(state=tk.DISABLED)
        
        self.update_answer_tab(None)
        self.update_stats_tab(None)
    
    def on_close(self):
        """关闭应用时的处理"""
        self.mistake_book.close()
        self.root.destroy()


class AddEditMistakeDialog:
    def __init__(self, parent, mistake_book, mistake_id=None, 
                 subject="", question_type="单选", question="", options=None, 
                 wrong_answer="", correct_answer="", explanation="", 
                 tags="", difficulty=3):
        self.mistake_book = mistake_book
        self.mistake_id = mistake_id
        
        self.top = tk.Toplevel(parent)
        self.top.title("添加错题" if mistake_id is None else "编辑错题")
        self.top.geometry("650x650")
        self.top.transient(parent)
        self.top.grab_set()
        
        # 创建表单框架
        form_frame = ttk.Frame(self.top)
        form_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 表单内容
        row = 0
        
        # 科目
        ttk.Label(form_frame, text="科目:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
        self.subject_var = tk.StringVar(value=subject)
        self.subject_combo = ttk.Combobox(form_frame, textvariable=self.subject_var)
        self.subject_combo.grid(row=row, column=1, padx=5, pady=5, sticky=tk.EW)
        self.subject_combo['values'] = self.mistake_book.get_subjects()
        row += 1
        
        # 题目类型
        ttk.Label(form_frame, text="题目类型:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
        self.type_var = tk.StringVar(value=question_type)
        self.type_combo = ttk.Combobox(form_frame, textvariable=self.type_var)
        self.type_combo.grid(row=row, column=1, padx=5, pady=5, sticky=tk.EW)
        self.type_combo['values'] = self.mistake_book.get_question_types()
        self.type_combo.bind("<<ComboboxSelected>>", self.update_form)
        row += 1
        
        # 难度
        ttk.Label(form_frame, text="难度(1-5):").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
        self.difficulty_var = tk.IntVar(value=difficulty)
        self.difficulty_spin = tk.Spinbox(form_frame, from_=1, to=5, textvariable=self.difficulty_var)
        self.difficulty_spin.grid(row=row, column=1, padx=5, pady=5, sticky=tk.W)
        row += 1
        
        # 标签
        ttk.Label(form_frame, text="标签(逗号分隔):").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
        self.tags_var = tk.StringVar(value=tags)
        ttk.Entry(form_frame, textvariable=self.tags_var).grid(
            row=row, column=1, padx=5, pady=5, sticky=tk.EW
        )
        row += 1
        
        # 题目
        ttk.Label(form_frame, text="题目:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
        row += 1
        self.question_text = scrolledtext.ScrolledText(form_frame, height=5)
        self.question_text.grid(row=row, column=0, columnspan=2, padx=5, pady=5, sticky=tk.EW)
        self.question_text.insert(tk.END, question)
        row += 1
        
        # 选项区域（选择题使用）
        self.options_frame = ttk.LabelFrame(form_frame, text="选项(仅选择题需要)")
        self.options_frame.grid(row=row, column=0, columnspan=2, padx=5, pady=5, sticky=tk.EW)
        row += 1
        
        self.option_entries = {}
        
        # 添加选项按钮
        option_button_frame = ttk.Frame(self.options_frame)
        option_button_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(option_button_frame, text="添加选项", command=self.add_option).pack(side=tk.LEFT)
        
        # 初始化选项
        self.option_list = []  # 存储选项标签
        self.option_content = {}  # 存储选项内容
        
        if options:
            for key, value in options.items():
                self.add_option(key, value)
        
        # 错误答案
        ttk.Label(form_frame, text="错误答案(可选):").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
        row += 1
        self.wrong_answer_text = scrolledtext.ScrolledText(form_frame, height=2)
        self.wrong_answer_text.grid(row=row, column=0, columnspan=2, padx=5, pady=5, sticky=tk.EW)
        self.wrong_answer_text.insert(tk.END, wrong_answer)
        row += 1
        
        # 正确答案
        ttk.Label(form_frame, text="正确答案:").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
        row += 1
        self.correct_answer_text = scrolledtext.ScrolledText(form_frame, height=2)
        self.correct_answer_text.grid(row=row, column=0, columnspan=2, padx=5, pady=5, sticky=tk.EW)
        self.correct_answer_text.insert(tk.END, correct_answer)
        row += 1
        
        # 解析
        ttk.Label(form_frame, text="解析(可选):").grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
        row += 1
        self.explanation_text = scrolledtext.ScrolledText(form_frame, height=4)
        self.explanation_text.grid(row=row, column=0, columnspan=2, padx=5, pady=5, sticky=tk.EW)
        self.explanation_text.insert(tk.END, explanation)
        row += 1
        
        # 按钮区域
        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="保存", command=self.save).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=self.top.destroy).pack(side=tk.LEFT, padx=5)
        
        # 初始更新表单
        self.update_form()
        
        # 配置网格布局
        form_frame.columnconfigure(1, weight=1)
        self.top.resizable(True, True)
    
    def update_form(self, event=None):
        """根据选择的题目类型更新表单"""
        q_type = self.type_var.get()
        
        if q_type in ["单选", "多选"]:
            self.options_frame.grid()
        else:
            self.options_frame.grid_remove()
    
    def add_option(self, key=None, value=None):
        """添加新的选项行"""
        row = len(self.option_entries)  # 当前选项行数
        
        # 如果未提供key，则使用大写字母作为标签
        if key is None:
            key = chr(65 + row)  # A, B, C, ...
        
        # 标签
        label_entry = ttk.Entry(self.options_frame, width=3)
        label_entry.insert(0, key)
        label_entry.grid(row=row, column=0, padx=5, pady=2, sticky=tk.W)
        
        # 选项内容
        content_entry = ttk.Entry(self.options_frame, width=40)
        if value:
            content_entry.insert(0, value)
        content_entry.grid(row=row, column=1, padx=5, pady=2, sticky=tk.EW)
        
        # 删除按钮
        delete_btn = ttk.Button(self.options_frame, text="×", width=2, 
                              command=lambda r=row: self.remove_option(r))
        delete_btn.grid(row=row, column=2, padx=5, pady=2, sticky=tk.E)
        
        # 存储条目
        self.option_entries[row] = (label_entry, content_entry, delete_btn)
    
    def remove_option(self, row):
        """移除指定行的选项"""
        if row in self.option_entries:
            # 销毁控件
            for widget in self.option_entries[row]:
                widget.destroy()
            
            # 删除条目
            del self.option_entries[row]
            
            # 重新排列剩余选项
            self.rearrange_options()
    
    def rearrange_options(self):
        """重新排列选项"""
        # 首先移除所有选项
        for widgets in self.option_entries.values():
            for widget in widgets:
                widget.destroy()
        
        # 重新添加所有选项
        self.option_entries = {}
        for idx, (key, value) in enumerate(self.get_options().items()):
            self.add_option(key, value)
    
    def get_options(self):
        """获取当前所有选项"""
        options = {}
        for row, (label_entry, content_entry, _) in self.option_entries.items():
            key = label_entry.get().strip()
            value = content_entry.get().strip()
            if key and value:
                options[key] = value
        return options
    
    def save(self):
        """保存错题"""
        # 获取表单数据
        subject = self.subject_var.get().strip()
        question_type = self.type_var.get().strip()
        question = self.question_text.get("1.0", tk.END).strip()
        options = self.get_options() if question_type in ["单选", "多选"] else None
        wrong_answer = self.wrong_answer_text.get("1.0", tk.END).strip()
        correct_answer = self.correct_answer_text.get("1.0", tk.END).strip()
        explanation = self.explanation_text.get("1.0", tk.END).strip()
        tags = self.tags_var.get().strip()
        difficulty = self.difficulty_var.get()
        
        # 验证输入
        if not subject:
            messagebox.showerror("错误", "科目不能为空")
            return
        if not question_type:
            messagebox.showerror("错误", "请选择题型")
            return
        if not question:
            messagebox.showerror("错误", "题目不能为空")
            return
        if question_type in ["单选", "多选"] and not options:
            messagebox.showerror("错误", "请至少添加一个选项")
            return
        if not correct_answer:
            messagebox.showerror("错误", "正确答案不能为空")
            return
        
        # 保存到数据库
        if self.mistake_id is None:
            self.mistake_book.add_mistake(
                subject, question_type, question, options, correct_answer, 
                explanation, tags, difficulty, wrong_answer
            )
        else:
            self.mistake_book.update_mistake(
                self.mistake_id, subject, question_type, question, options, 
                correct_answer, explanation, tags, difficulty, wrong_answer
            )
        
        self.top.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = MistakeBookGUI(root)
    root.mainloop()