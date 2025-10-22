import os
instance_path = '/home/henryjia/Projects/flask_stock_plot/instance'
file_path = os.path.join(instance_path, 'test.txt')
try:
    with open(file_path, 'w') as f:
        f.write('hello')
        print(f"File created at {file_path}")
except Exception as e:
    print(f"An error occurred: {e}")

