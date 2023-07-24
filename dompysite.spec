# -*- mode: python -*-
 
block_cipher = None
 
 
a = Analysis(['dompysite.py'],
             pathex=['d:\\dom\\core\\pysite', 'D:\\dom\\core\\pysite'],
             binaries=[],
             datas=[("C:\\Python34\\Lib\\site-packages\\aliyunsdkcore\\data", "aliyunsdkcore\\data\\"),
             ("C:\\Python34\\Lib\\site-packages\\sklearn", "sklearn\\"),
             ("C:\\Python34\\Lib\\site-packages\\dateutil", "dateutil\\")],
             hiddenimports=['sklearn.neighbors.typedefs', 'sklearn.neighbors.quad_tree', 'sklearn.tree._utils'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='dompysite',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='dompysite')