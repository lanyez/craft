#
# copyright (c) 2012 Patrick von Reth <vonreth@kde.org>
#
# definitions for the qt5 modules 

from BuildSystem.QMakeBuildSystem import *


class Qt5CoreBuildSystem( QMakeBuildSystem ):
    def __init__( self ):
        QMakeBuildSystem.__init__( self )
        utils.putenv( "QMAKESPEC", os.path.join( EmergeStandardDirs.emergeRoot( ), 'mkspecs', self.platform ) )


    def install( self, options = "" ):
        """implements the make step for Qt projects"""
        options += " INSTALL_ROOT=%s install" % self.imageDir( )
        if not QMakeBuildSystem.install( self, options ):
            return False

        if os.path.exists( os.path.join( self.installDir( ), "bin", "mkspecs" ) ):
            utils.moveFile( os.path.join( self.installDir( ), "bin", "mkspecs" ),
                            os.path.join( self.installDir( ), "mkspecs" ) )
        return True



          

