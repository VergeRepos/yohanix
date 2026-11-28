# Copyright 2026 Gentoo Authors
# Distributed under the terms of the MIT License

EAPI=8

PYTHON_COMPAT=( python3_12 )
inherit python-single-r1

DESCRIPTION="Local stock research and alert system"
HOMEPAGE="https://github.com/NyohickLabs/stockpulse"
SRC_URI="https://github.com/NyohickLabs/stockpulse/archive/refs/tags/v${PV}.tar.gz -> ${P}.tar.gz"

LICENSE="MIT"
SLOT="0"
KEYWORDS="~amd64 ~x86"
IUSE="test"

REQUIRED_USE="${PYTHON_REQUIRED_USE}"

RDEPEND="
	${PYTHON_DEPS}
	>=dev-python/lumibot-3.0[${PYTHON_USEDEP}]
	>=dev-python/yfinance-0.2[${PYTHON_USEDEP}]
	>=dev-python/edgartools-3.0[${PYTHON_USEDEP}]
	>=dev-python/pandas-2.0[${PYTHON_USEDEP}]
	>=dev-python/pandas-ta-0.3[${PYTHON_USEDEP}]
	>=dev-python/anthropic-0.40[${PYTHON_USEDEP}]
	>=dev-python/apscheduler-3.10[${PYTHON_USEDEP}]
	>=dev-python/pyyaml-6.0[${PYTHON_USEDEP}]
	>=dev-python/python-dotenv-1.0[${PYTHON_USEDEP}]
	>=dev-python/jinja2-3.1[${PYTHON_USEDEP}]
	>=dev-python/requests-2.31[${PYTHON_USEDEP}]
	>=dev-python/pytz-2024.1[${PYTHON_USEDEP}]
	>=dev-python/python-telegram-bot-21.0[${PYTHON_USEDEP}]
	>=dev-python/fastapi-0.115[${PYTHON_USEDEP}]
	>=dev-python/uvicorn-0.30[${PYTHON_USEDEP}]
"
BDEPEND="${RDEPEND}"

src_prepare() {
	default
}

src_compile() {
	python_optimize
}

src_install() {
	python_domodule stockpulse
	newbin run.py stockpulse
	insinto /etc/stockpulse
	newins .env.example .env
	newinitd "${FILESDIR}/stockpulse.initd" stockpulse
	newconfd "${FILESDIR}/stockpulse.confd" stockpulse
}
