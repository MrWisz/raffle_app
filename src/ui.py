import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from PIL import Image, ImageTk, ImageDraw
import src.core as core
import src.config_manager as config_manager
import os
import json

class ImageEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Raffle Manager Pro")
        
        self.config = config_manager.load_config()
        self.max_display_width = 800
        self.max_display_height = 600

        # Estado de la aplicación
        self.original_image = None
        self.clean_image = None
        self.tk_image = None
        self.scale_factor = 1.0
        self.image_history = []  
        self.raffle_data = {}    
        self.calibrating = False
        self.grid_points = []
        self.grid_rect = None
        self.current_color = self.config.get("x_color", "black")
        self.unsaved_changes = False
        
        # Tooltip para el Hover
        self.tooltip = tk.Label(root, text="", bg="#FFFFCA", fg="black", 
                               relief=tk.SOLID, borderwidth=1, font=("Arial", 10, "bold"), 
                               padx=8, pady=4)
        self.tooltip.place_forget()

        self.setup_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_ui(self):
        vcmd = (self.root.register(self.validate_input_format), '%S')

        # --- Barra Superior ---
        top_frame = tk.Frame(self.root)
        top_frame.pack(pady=10, fill=tk.X)
        
        tk.Button(top_frame, text="Abrir Imagen", command=self.open_image).pack(side=tk.LEFT, padx=5)
        self.btn_save_proj = tk.Button(top_frame, text="Guardar Proyecto", command=self.save_project, state=tk.DISABLED)
        self.btn_save_proj.pack(side=tk.LEFT, padx=5)
        tk.Button(top_frame, text="Cargar Proyecto", command=self.load_project).pack(side=tk.LEFT, padx=5)
        self.btn_grid = tk.Button(top_frame, text="Calibrar", command=self.start_calibration, state=tk.DISABLED)
        self.btn_grid.pack(side=tk.LEFT, padx=5)
        self.btn_undo = tk.Button(top_frame, text="Deshacer", command=self.undo, state=tk.DISABLED)
        self.btn_undo.pack(side=tk.LEFT, padx=5)
        self.btn_clear = tk.Button(top_frame, text="Limpiar Todo", command=self.clear_all, state=tk.DISABLED, fg="red")
        self.btn_clear.pack(side=tk.LEFT, padx=5)
        
        export_frame = tk.Frame(top_frame)
        export_frame.pack(side=tk.RIGHT, padx=5)
        tk.Button(export_frame, text="Exportar JSON", command=self.export_to_json, bg="#f0f0f0").pack(side=tk.LEFT, padx=2)
        tk.Button(export_frame, text="Exportar PNG", command=self.save_image, bg="#e1e1e1").pack(side=tk.LEFT, padx=2)

        # --- Barra Lateral ---
        side_frame = tk.Frame(self.root, width=150)
        side_frame.pack(side=tk.LEFT, padx=10, fill=tk.Y)
        
        tk.Label(side_frame, text="Rango Rifa:", font=("Arial", 9, "bold")).pack(pady=(10,0))
        range_frame = tk.Frame(side_frame)
        range_frame.pack()
        self.ent_min = tk.Entry(range_frame, width=5); self.ent_min.insert(0, "0"); self.ent_min.grid(row=0, column=1)
        self.ent_max = tk.Entry(range_frame, width=5); self.ent_max.insert(0, "99"); self.ent_max.grid(row=1, column=1)

        tk.Label(side_frame, text="Marcar (Ej: 1,2 o 5-10):", font=("Arial", 8, "bold")).pack(pady=(15,0))
        self.ent_num = tk.Entry(side_frame, width=15, font=("Arial", 11), validate='key', validatecommand=vcmd)
        self.ent_num.pack(pady=5)
        self.ent_num.bind("<Return>", lambda e: self.process_input_request())
        tk.Button(side_frame, text="Marcar", command=self.process_input_request, bg="lightgreen").pack(fill=tk.X)

        tk.Label(side_frame, text="Ventas:", font=("Arial", 9, "bold")).pack(pady=(20,0))
        self.sales_counter = tk.Label(side_frame, text="0", font=("Arial", 18, "bold"), fg="darkgreen")
        self.sales_counter.pack()

        # --- Área Central ---
        self.status_label = tk.Label(self.root, text="Carga una imagen", fg="blue")
        self.status_label.pack()
        self.canvas = tk.Canvas(self.root, bg="gray", relief=tk.SUNKEN, border=2)
        self.canvas.pack(expand=True)
        
        self.canvas.bind("<Button-1>", self.handle_click)
        self.canvas.bind("<Motion>", self.handle_hover)
        self.canvas.bind("<Leave>", lambda e: self.hide_tooltip())

    def validate_input_format(self, char):
        return char.isdigit() or char in ",-"

    def process_input_request(self):
        if not self.grid_rect:
            messagebox.showwarning("Aviso", "Calibra la cuadrícula primero.")
            return

        raw_val = self.ent_num.get().strip()
        if not raw_val: return

        nums_to_mark = set()
        try:
            parts = raw_val.split(',')
            for part in parts:
                if '-' in part:
                    start_str, end_str = part.split('-')
                    nums_to_mark.update(range(int(start_str), int(end_str) + 1))
                else:
                    nums_to_mark.add(int(part))
            
            r_min, r_max = int(self.ent_min.get()), int(self.ent_max.get())
            valid_nums = [n for n in nums_to_mark if r_min <= n <= r_max and n not in self.raffle_data]
            
            if not valid_nums:
                messagebox.showinfo("Aviso", "Números no válidos o ya marcados.")
                return

            name = simpledialog.askstring("Comprador", f"¿Nombre para estos {len(valid_nums)} números?")
            if not name: return

            self.save_history_state()
            for n in valid_nums:
                self.mark_logic(n, name)
            
            self.ent_num.delete(0, tk.END)
            self.update_display_after_batch()

        except Exception:
            messagebox.showerror("Error", "Formato inválido. Usa ej: 1,2,5-10")

    def handle_click(self, event):
        if not self.original_image: return
        if self.calibrating:
            self.grid_points.append((event.x, event.y))
            if len(self.grid_points) == 2:
                x1, y1 = self.grid_points[0]; x2, y2 = event.x, event.y
                self.grid_rect = (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
                self.calibrating = False
                self.status_label.config(text="Calibración lista.", fg="green")
            return
        
        if self.grid_rect:
            res = core.calculate_snap(event.x, event.y, self.grid_rect)
            if res:
                start = int(self.ent_min.get())
                num = start + (res[2] * 10) + res[3]
                
                if num in self.raffle_data:
                    messagebox.showinfo("Vendido", f"El {num} ya es de: {self.raffle_data[num]}")
                    return
                
                name = simpledialog.askstring("Comprador", f"¿Nombre para el número {num}?")
                if name:
                    self.save_history_state()
                    self.mark_logic(num, name)
                    self.update_display_after_batch()

    def mark_logic(self, num, name):
        start = int(self.ent_min.get())
        idx = num - start
        row, col = idx // 10, idx % 10
        
        x_start, y_start, x_end, y_end = self.grid_rect
        cell_w, cell_h = (x_end - x_start) / 10, (y_end - y_start) / 10
        dx = x_start + (col + 0.5) * cell_w
        dy = y_start + (row + 0.5) * cell_h

        s, t = 10, 4
        self.canvas.create_line(dx-s, dy-s, dx+s, dy+s, fill=self.current_color, width=t, tags="mark")
        self.canvas.create_line(dx-s, dy+s, dx+s, dy-s, fill=self.current_color, width=t, tags="mark")
        
        ox, oy = int(dx/self.scale_factor), int(dy/self.scale_factor)
        os, ot = int(s/self.scale_factor), max(1, int(t/self.scale_factor))
        draw = ImageDraw.Draw(self.original_image)
        draw.line((ox-os, oy-os, ox+os, oy+os), fill=self.current_color, width=ot)
        draw.line((ox-os, oy+os, ox+os, oy-os), fill=self.current_color, width=ot)
        
        self.raffle_data[num] = name

    def handle_hover(self, event):
        if not self.grid_rect: return
        
        res = core.calculate_snap(event.x, event.y, self.grid_rect)
        self.canvas.delete("hover_highlight")
        
        if res:
            start = int(self.ent_min.get())
            num = start + (res[2] * 10) + res[3]
            
            x_start, y_start, x_end, y_end = self.grid_rect
            cw, ch = (x_end - x_start) / 10, (y_end - y_start) / 10
            x0 = x_start + (res[3] * cw)
            y0 = y_start + (res[2] * ch)
            self.canvas.create_rectangle(x0, y0, x0+cw, y0+ch, outline="cyan", width=2, tags="hover_highlight")

            if num in self.raffle_data:
                self.tooltip.config(text=f" Número {num}: {self.raffle_data[num]} ")
                tx = event.x_root - self.root.winfo_rootx() + 15
                ty = event.y_root - self.root.winfo_rooty() + 15
                self.tooltip.place(x=tx, y=ty)
                self.tooltip.lift()
                return
                
        self.hide_tooltip()

    def hide_tooltip(self):
        self.tooltip.place_forget()
        self.canvas.delete("hover_highlight")

    def perform_save_logic(self, fp):
        """Lógica centralizada para guardar .rifa y .json"""
        try:
            # Guardar archivo de proyecto (.rifa)
            core.save_project_file(fp, self.original_image, self.clean_image, self.grid_rect, self.raffle_data)
            
            # Generar ruta y guardar JSON automáticamente
            json_fp = os.path.splitext(fp)[0] + ".json"
            sorted_data = {str(k): self.raffle_data[k] for k in sorted(self.raffle_data.keys())}
            with open(json_fp, 'w', encoding='utf-8') as f:
                json.dump(sorted_data, f, indent=4, ensure_ascii=False)
            
            self.unsaved_changes = False
            return True
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar: {e}")
            return False

    def save_project(self):
        fp = filedialog.asksaveasfilename(defaultextension=".rifa", filetypes=[("Proyecto", "*.rifa")])
        if fp:
            if self.perform_save_logic(fp):
                messagebox.showinfo("Éxito", "Proyecto y lista JSON guardados.")

    def export_to_json(self):
        """Exportación manual si solo se desea el JSON"""
        if not self.raffle_data:
            messagebox.showwarning("Vacio", "No hay datos para exportar.")
            return
        fp = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if fp:
            sorted_data = {str(k): self.raffle_data[k] for k in sorted(self.raffle_data.keys())}
            with open(fp, 'w', encoding='utf-8') as f:
                json.dump(sorted_data, f, indent=4, ensure_ascii=False)
            messagebox.showinfo("Éxito", "JSON exportado.")

    def save_history_state(self):
        self.image_history.append((self.original_image.copy(), dict(self.raffle_data)))
        self.btn_undo.config(state=tk.NORMAL)
        self.unsaved_changes = True

    def undo(self):
        if self.image_history:
            prev_img, prev_data = self.image_history.pop()
            self.original_image = prev_img
            self.raffle_data = prev_data
            self.update_display()
            if not self.image_history: self.btn_undo.config(state=tk.DISABLED)

    def update_display(self):
        if not self.original_image: return
        self.canvas.delete("all")
        self.hide_tooltip()
        orig_w, orig_h = self.original_image.size
        scale = min(self.max_display_width/orig_w, self.max_display_height/orig_h)
        self.scale_factor = scale
        new_w, new_h = int(orig_w*scale), int(orig_h*scale)
        img_res = self.original_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(img_res)
        self.canvas.config(width=new_w, height=new_h)
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)
        self.btn_grid.config(state=tk.NORMAL); self.btn_save_proj.config(state=tk.NORMAL); self.btn_clear.config(state=tk.NORMAL)
        self.update_counter()

    def update_display_after_batch(self):
        self.update_display()
        self.status_label.config(text="Operación exitosa", fg="green")

    def update_counter(self):
        self.sales_counter.config(text=str(len(self.raffle_data)))

    def open_image(self):
        fp = filedialog.askopenfilename(filetypes=[("Imágenes", "*.png *.jpg *.jpeg")])
        if fp:
            self.original_image = Image.open(fp).convert("RGBA")
            self.clean_image = self.original_image.copy()
            self.raffle_data = {}; self.image_history = []
            self.update_display()

    def load_project(self):
        fp = filedialog.askopenfilename(filetypes=[("Proyecto", "*.rifa")])
        if fp:
            data = core.load_project_file(fp)
            self.original_image = data["image"]
            self.clean_image = data.get("clean_image", self.original_image.copy())
            self.grid_rect = data["grid_rect"]
            self.raffle_data = {int(k): v for k, v in data.get("raffle_data", {}).items()}
            self.image_history = []
            self.update_display()

    def clear_all(self):
        if messagebox.askyesno("Limpiar", "¿Borrar todas las ventas?"):
            self.original_image = self.clean_image.copy()
            self.raffle_data = {}; self.image_history = []
            self.update_display()

    def start_calibration(self):
        self.calibrating = True; self.grid_points = []
        self.status_label.config(text="Calibrando: Clic en Sup-Izq y luego Inf-Der", fg="red")

    def save_image(self):
        fp = filedialog.asksaveasfilename(defaultextension=".png")
        if fp: self.original_image.save(fp)

    def on_closing(self):
        """Actualizado: Si hay cambios, permite guardar ambos formatos antes de salir"""
        if self.unsaved_changes:
            ans = messagebox.askyesnocancel("Salir", "¿Deseas guardar los cambios antes de salir?")
            if ans is True: # El usuario eligió GUARDAR
                fp = filedialog.asksaveasfilename(defaultextension=".rifa", filetypes=[("Proyecto", "*.rifa")])
                if fp and self.perform_save_logic(fp):
                    self.root.destroy()
            elif ans is False: # El usuario eligió NO GUARDAR
                self.root.destroy()
        else:
            self.root.destroy()

    def validate_only_numbers(self, char): return char.isdigit()