import os

def list_files(startpath):
    exclude = {'__pycache__', 'venv', '.git', '.DS_Store'}
    
    print(f"\nProject Structure for: {os.path.basename(startpath)}\n")
    
    for root, dirs, files in os.walk(startpath):
        # Remove excluded directories
        dirs[:] = [d for d in dirs if d not in exclude]
        
        level = root.replace(startpath, '').count(os.sep)
        indent = '    ' * level
        print(f'{indent}{os.path.basename(root)}/')
        subindent = '    ' * (level + 1)
        for f in sorted(files):
            if not f.endswith('.pyc') and f not in exclude and not f.startswith('.'):
                print(f'{subindent}{f}')

if __name__ == "__main__":
    list_files('.')