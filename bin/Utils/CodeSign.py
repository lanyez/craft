# -*- coding: utf-8 -*-
# Copyright Hannah von Reth <vonreth@kde.org>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

import os
from pathlib import Path
import subprocess
import secrets

from CraftCore import CraftCore
from CraftOS.osutils import OsUtils, LockFile
from CraftSetupHelper import SetupHelper
from Utils import CraftChoicePrompt, CraftCache
import utils


def signWindows(fileNames : [str]) -> bool:
    if not CraftCore.settings.getboolean("CodeSigning", "Enabled", False):
        return True
    if not CraftCore.compiler.isWindows:
        CraftCore.log.warning("Code signing is currently only supported on Windows")
        return True

    signTool = CraftCore.cache.findApplication("signtool", forceCache=True)
    if not signTool:
        env = SetupHelper.getMSVCEnv()
        signTool = CraftCore.cache.findApplication("signtool", env["PATH"], forceCache=True)
    if not signTool:
        CraftCore.log.warning("Code signing requires a VisualStudio installation")
        return False

    command = [signTool, "sign", "/tr", "http://timestamp.digicert.com", "/td", "SHA256", "/fd", "SHA256", "/a"]
    certFile = CraftCore.settings.get("CodeSigning", "Certificate", "")
    subjectName = CraftCore.settings.get("CodeSigning", "CommonName", "")
    certProtected = CraftCore.settings.getboolean("CodeSigning", "Protected", False)
    kwargs = dict()
    if certFile:
        command += ["/f", certFile]
    if subjectName:
        command += ["/n", subjectName]
    if certProtected:
        password = CraftChoicePrompt.promptForPassword(message='Enter the password for your package signing certificate', key="WINDOWS_CODE_SIGN_CERTIFICATE_PASSWORD")
        command += ["/p", password]
        kwargs["secret"] = [password]
    if True or CraftCore.debug.verbose() > 0:
        command += ["/v"]
    else:
        command += ["/q"]
    for args in utils.limitCommandLineLength(command, fileNames):
        if not utils.system(args, **kwargs):
            return False
    return True

class _MacSignScope(LockFile, utils.ScopedEnv):
    __REAL_HOME = None
    def __init__(self):
        LockFile.__init__(self, "keychainLock")
        # ci setups tend to mess with the env and we need the users real home
        if not _MacSignScope.__REAL_HOME:
            user =  subprocess.getoutput("id -un")
            _MacSignScope.__REAL_HOME = Path("/Users") / user
        utils.ScopedEnv.__init__(self, {"HOME": str(_MacSignScope.__REAL_HOME)})
        self.certFileApplication = CraftCore.settings.get("CodeSigning", "MacCertificateApplication", "")
        self.certFilesInstaller = CraftCore.settings.get("CodeSigning", "MacCertificateInstaller", "")

        # FIXME: loginKeychain is misleading - it doesn't need to be login.keychain
        if self._useCertFile:
            self.loginKeychain = f"craft-{secrets.token_urlsafe(16)}.keychain"
        else:
            self.loginKeychain = CraftCore.settings.get("CodeSigning", "MacKeychainPath", os.path.expanduser("~/Library/Keychains/login.keychain"))



    @property
    def _useCertFile(self):
        return self.certFileApplication or self.certFilesInstaller

    def __unlock(self):
        if self._useCertFile:
            password = secrets.token_urlsafe(16)
            if not utils.system(["security", "create-keychain", "-p", password, self.loginKeychain], stdout=subprocess.DEVNULL, secret=[password]):
                return False

            def importCert(cert, pwKey):
                pw  = CraftChoicePrompt.promptForPassword(message=f"Enter the password for certificate: {Path(cert).name}", key=pwKey)
                return utils.system(["security", "import", cert, "-k", self.loginKeychain, "-P", pw, "-T", "/usr/bin/codesign", "-T", "/usr/bin/productsign"], stdout=subprocess.DEVNULL, secret=[password])

            if self.certFileApplication:
                if not importCert(self.certFileApplication, "MAC_CERTIFICATE_APPLICATION_PASSWORD"):
                    return False
            if self.certFilesInstaller:
                if not importCert(self.certFilesInstaller, "MAC_CERTIFICATE_INSTALLER_PASSWORD"):
                    return False
            # needed for productsign, codesign works without
            if not utils.system(["security", "set-key-partition-list", "-S", "apple-tool:,apple:,codesign:", "-s", "-k", password, self.loginKeychain], stdout=subprocess.DEVNULL, secret=[password]):
                CraftCore.log.error("Failed to set key partition list.")
                return False
        else:
            if CraftCore.settings.getboolean("CodeSigning", "Protected", False):
                password = CraftChoicePrompt.promptForPassword(message="Enter the password for your signing keychain", key="MAC_KEYCHAIN_PASSWORD")
                if not utils.system(["security", "unlock-keychain", "-p", password, self.loginKeychain], stdout=subprocess.DEVNULL, secret=[password]):
                    CraftCore.log.error("Failed to unlock keychain.")
                    return False

        return True

    def __enter__(self):
        LockFile.__enter__(self)
        utils.ScopedEnv.__enter__(self)
        if not self.__unlock():
            raise Exception("Failed to setup keychain")
            return None
        return self

    def __exit__(self, exc_type, exc_value, trback):
        if self._useCertFile:
            utils.system(["security", "delete-keychain", self.loginKeychain])
        utils.ScopedEnv.__exit__(self, exc_type, exc_value, trback)
        LockFile.__exit__(self, exc_type, exc_value, trback)

def signMacApp(appPath : str):
    if not CraftCore.settings.getboolean("CodeSigning", "Enabled", False):
        return True
    # special case, two independent setups of craft might want to sign at the same time and only one keychain can be unlocked at a time
    with _MacSignScope() as scope:
        devID = CraftCore.settings.get("CodeSigning", "MacDeveloperId")

        # Recursively sign app
        if not utils.system(["codesign", "--keychain", scope.loginKeychain, "--sign", f"Developer ID Application: {devID}", "--force", "--preserve-metadata=entitlements", "--options", "runtime", "--verbose=99", "--deep", appPath]):
            return False

        ## Verify signature
        if not utils.system(["codesign", "--display", "--verbose", appPath]):
            return False

        if not utils.system(["codesign", "--verify", "--verbose", "--strict", appPath]):
            return False

        # TODO: this step might require notarisation
        utils.system(["spctl", "-a", "-t", "exec", "-vv", appPath])

        ## Validate that the key used for signing the binary matches the expected TeamIdentifier
        ## needed to pass the SocketApi through the sandbox
        #if not utils.system("codesign -dv %s 2>&1 | grep 'TeamIdentifier=%s'" % (self.appPath, teamIdentifierFromConfig)):
                #return False

        return True

def signMacPackage(packagePath : str):
    if not CraftCore.settings.getboolean("CodeSigning", "Enabled", False):
        return True

    # special case, two independent setups of craft might want to sign at the same time and only one keychain can be unlocked at a time
    with _MacSignScope() as scope:
        packagePath = Path(packagePath)
        devID = CraftCore.settings.get("CodeSigning", "MacDeveloperId")

        if packagePath.name.endswith(".dmg"):
            # sign dmg
            if not utils.system(["codesign", "--force", "--keychain", scope.loginKeychain, "--sign", f"Developer ID Application: {devID}", packagePath]):
                return False

            # TODO: this step would require notarisation
            # verify dmg signature
            utils.system(["spctl", "-a", "-t", "open", "--context", "context:primary-signature", packagePath])
        else:
            # sign pkg
            packagePathTmp = f"{packagePath}.sign"
            if not utils.system(["productsign", "--keychain", scope.loginKeychain, "--sign", f"Developer ID Installer: {devID}", packagePath, packagePathTmp]):
                return False

            utils.moveFile(packagePathTmp, packagePath)

        return True
