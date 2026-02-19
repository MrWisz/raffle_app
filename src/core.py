import pickle

def calculate_snap(click_x, click_y, grid_rect):
    """Calcula el centro de la celda basada en un grid de 10x10."""
    x_start, y_start, x_end, y_end = grid_rect
    if not (x_start <= click_x <= x_end and y_start <= click_y <= y_end):
        return None
    
    cell_w = (x_end - x_start) / 10
    cell_h = (y_end - y_start) / 10
    col = int((click_x - x_start) / cell_w)
    row = int((click_y - y_start) / cell_h)
    
    snapped_x = x_start + (col + 0.5) * cell_w
    snapped_y = y_start + (row + 0.5) * cell_h
    return snapped_x, snapped_y, row, col

# Actualiza estas funciones en src/core.py
def save_project_file(filepath, original_img, clean_img, grid_rect, raffle_data):
    data = {
        "image": original_img,
        "clean_image": clean_img,
        "grid_rect": grid_rect,
        "raffle_data": raffle_data
    }
    with open(filepath, 'wb') as f:
        pickle.dump(data, f)

def load_project_file(filepath):
    with open(filepath, 'rb') as f:
        return pickle.load(f)