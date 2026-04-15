import shutil
import os

# 删除 core/roles 目录
roles_dir = "core/roles"
if os.path.exists(roles_dir):
    shutil.rmtree(roles_dir)
    print(f"✓ Deleted: {roles_dir}")
else:
    print(f"✓ Already deleted: {roles_dir}")

# 验证
if os.path.exists(roles_dir):
    print(f"✗ Failed to delete: {roles_dir}")
else:
    print(f"✓ Verified: {roles_dir} does not exist")
