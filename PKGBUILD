pkgname=game-engine-finder-git
pkgver=r18.f788f96
pkgrel=1
pkgdesc="Python script for easily figuring out the engine used for a game"
arch=('any')
url="https://github.com/vetleledaal/game-engine-finder"
license=('MIT')
groups=()
depends=('python')
makedepends=('git')
provides=("${pkgname%-git}")
conflicts=("${pkgname%-git}")
replaces=()
backup=()
options=()
install=
source=('game-engine-finder::git+https://github.com/vetleledaal/game-engine-finder.git')
noextract=()
md5sums=('SKIP')

pkgver() {
        cd "$srcdir/${pkgname%-git}"
        printf "r%s.%s" "$(git rev-list --count HEAD)" "$(git rev-parse --short HEAD)"
}

package() {
        cd "$srcdir/${pkgname%-git}"
        install -Dm755 find-engine.py ${pkgdir}/usr/bin/find-engine
}
