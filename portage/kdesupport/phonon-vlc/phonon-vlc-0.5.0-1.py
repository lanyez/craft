# -*- coding: utf-8 -*-
import info
import os
import compiler
from Package.CMakePackageBase import *


class subinfo(info.infoclass):
    def setDependencies( self ):
        self.dependencies['kdesupport/phonon'] = 'default'
        self.dependencies['binary/vlc'] = 'default'
        if compiler.isMSVC() or compiler.isIntel():
            self.dependencies['kdesupport/kdewin'] = 'default'

    def setTargets( self ):
      self.targets['0.3.1'] = "http://download.kde.org/download.php?url=stable/phonon-backend-vlc/0.3.1/src/phonon-backend-vlc-0.3.1.tar.bz2"
      self.targetInstSrc['0.3.1'] = "phonon-backend-vlc-0.3.1"
      self.targetDigests['0.3.1'] = 'b94dddc6f37924c101a8bab7b7a184b7d6b42d96'
      self.patchToApply['0.3.1'] = ("phonon-backend-vlc-0.3.1-20101223.diff", 1)
      self.targets['0.4.1'] = "http://download.kde.org/download.php?url=stable/phonon/phonon-backend-vlc/0.4.1/phonon-backend-vlc-0.4.1.tar.xz"
      self.targetInstSrc['0.4.1'] = "phonon-backend-vlc-0.4.1"
      self.targetDigests['0.4.1'] = 'b2957b70e1722f08a231b9e64acfafb799b52d11'
      
      self.patchToApply['0.4.1'] = [("phonon-backend-vlc-0.4.1-20111213.diff", 1),("phonon-backend-vlc-0.4.1-20111223.diff",1)]
      for ver in ['0.5.0', '0.6.0', '0.6.1', '0.7.0', '0.7.1']:
        self.targets[ ver ] = "http://download.kde.org/stable/phonon/phonon-backend-vlc/%s/src/phonon-backend-vlc-%s.tar.xz" % ( ver ,ver )
        self.targetInstSrc[ ver ] = "phonon-backend-vlc-%s" % ver 
        
      for ver in ['0.6.2']:
        self.targets[ ver ] = "http://download.kde.org/download.php?url=stable/phonon/phonon-backend-vlc/%s/phonon-backend-vlc-%s.tar.xz" % ( ver ,ver )
        self.targetInstSrc[ ver ] = "phonon-backend-vlc-%s" % ver 
        
      self.targetDigests['0.6.0'] = 'f66a70cd27ad49dc98eb6526d0566cfe0802774b'
      self.targetDigests['0.6.1'] = '2c17bd124a2f6543efc6af0e6a79bf37f8f5cd37'
      
      self.patchToApply['0.5.0'] = [("0001-Revert-stop-leaking-video-audio-abstraction.patch",1)]
      self.patchToApply['0.6.0'] = [("fix windows aout selection.diff",1)]
      self.patchToApply['0.6.2'] = [("do not mark injected devices as advanced.diff",1),
                                    ("use-kdewin-also-for-intel-compiler.diff", 1)]
      self.patchToApply['0.7.0'] = [("use-kdewin-also-for-intel-compiler.diff", 1),
                                    ("0002-FindLIBVLC-Detect-libvlc-s-version-even-if-pkg-confi.patch", 1)]
      
      self.svnTargets['gitHEAD'] = '[git]kde:phonon-vlc'
      
      self.shortDescription = "the vlc based phonon multimedia backend"
      self.defaultTarget = '0.7.1'


class Package( CMakePackageBase ):
    def __init__( self, **args ):
        self.subinfo = subinfo()
        CMakePackageBase.__init__(self)
        self.subinfo.options.configure.defines = '-DCMAKE_CXX_FLAGS=-DWIN32 -DPHONON_BUILDSYSTEM_DIR=\"%s;%s\" ' % (os.path.join(os.getenv('KDEROOT'),'share','phonon','buildsystem').replace('\\','/'),os.path.join(os.getenv('KDEROOT'),'share','phonon-buildsystem').replace('\\','/'))

if __name__ == '__main__':
    Package().execute()
