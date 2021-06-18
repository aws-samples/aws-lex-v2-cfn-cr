MAKEFLAGS += --warn-undefined-variables
SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := all
.DELETE_ON_ERROR:
.SUFFIXES:

all: build
.PHONY: all

# This maps to the sam cli --config-env option. You can overrided it using
# by exporting the CONFIG_ENV variable in your shell. It defaults to: "default"
export CONFIG_ENV ?= default

ifndef CONFIG_ENV
$(error [ERROR] - CONFIG_ENV environmental variable\
 to map to the sam config-env option is not set)
endif

all: build
.PHONY: all

TEMPLATE_FILE ?= template.yaml
SAMCONFIG_FILE ?= samconfig.toml
SAM_BUILD_DIR ?= .aws-sam
SRC_DIR := src

OUT_DIR ?= out
$(OUT_DIR):
	@echo '[INFO] creating build output dir: [$(@)]'
	mkdir -p '$(@)'

##########################################################################
# Install
#
# Install build dependencies. Should only be needed before first run or
# if updating build dependencies
##########################################################################

PYTHON_VERSION ?= 3.8
# python virtual environment directory
VIRTUALENV_DIR ?= $(OUT_DIR)/venv
VENV_CFG := $(VIRTUALENV_DIR)/pyvenv.cfg
$(VENV_CFG): | $(OUT_DIR)
	echo "[INFO] Creating python virtual env under directory: [$(VIRTUALENV_DIR)]"
	python$(PYTHON_VERSION) -m venv '$(VIRTUALENV_DIR)'
install-python-venv: $(VENV_CFG)
.PHONY: install-python-venv

VIRTUALENV_BIN_DIR ?= $(VIRTUALENV_DIR)/bin
PYTHON_REQUIREMENTS_DIR ?= requirements
PYTHON_BUILD_REQUIREMENTS := $(PYTHON_REQUIREMENTS_DIR)/requirements-build.txt
PYTHON_DEV_REQUIREMENTS := $(PYTHON_REQUIREMENTS_DIR)/requirements-dev.txt

PYTHON_SRC_REQUIREMENTS := $(PYTHON_DEV_REQUIREMENTS) $(PYTHON_BUILD_REQUIREMENTS)
PYTHON_TARGET_REQUIREMENTS := $(patsubst \
	$(PYTHON_REQUIREMENTS_DIR)/%, \
	$(OUT_DIR)/%, \
	$(PYTHON_SRC_REQUIREMENTS) \
)

$(PYTHON_TARGET_REQUIREMENTS): $(OUT_DIR)/%: $(PYTHON_REQUIREMENTS_DIR)/% | $(OUT_DIR) $(VENV_CFG)
	@echo "[INFO] Installing python dependencies file: [$(^)]"
	@source '$(VIRTUALENV_BIN_DIR)/activate' && \
		pip install -r $(^) | tee $(@)
install-python-requirements: $(PYTHON_TARGET_REQUIREMENTS)
.PHONY: install-python-requirements

install: install-python-venv install-python-requirements
.PHONY: install

# prepend python virtual env bin directory to path
VIRTUALENV_BIN_DIR ?= "$(VIRTUALENV_DIR)/bin"
export PATH := "$(VIRTUALENV_BIN_DIR):$(PATH)"
export VIRTUALENV_DIR

##########################################################################
# build
##########################################################################
SAM_CMD ?= $(VIRTUALENV_BIN_DIR)/sam
$(SAM_CMD): $(PYTHON_TARGET_REQUIREMENTS)

LAMBDA_FUNCTIONS_DIR := $(SRC_DIR)/lambda_functions
LAMBDA_FUNCTIONS := $(wildcard $(LAMBDA_FUNCTIONS_DIR)/*)
LAMBDA_FUNCTIONS_SRC_FILES := $(wildcard \
	$(LAMBDA_FUNCTIONS_DIR)/**/*.py \
	$(LAMBDA_FUNCTIONS_DIR)/**/**/*.py \
	$(LAMBDA_FUNCTIONS_DIR)/**/requirements.txt \
)
LAMBDA_LAYERS_DIR := $(SRC_DIR)/lambda_layers
LAMBDA_LAYERS := $(wildcard $(LAMBDA_LAYERS_DIR)/*)
LAMBDA_LAYERS_SRC_FILES := $(wildcard \
	$(LAMBDA_LAYERS_DIR)/**/*.py \
	$(LAMBDA_LAYERS_DIR)/**/**/*.py \
	$(LAMBDA_LAYERS_DIR)/**/requirements.txt \
	$(LAMBDA_LAYERS_DIR)/**/Makefile \
)
STATE_MACHINES_DIR := $(SRC_DIR)/state_machines
STATE_MACHINES := $(wildcard $(STATE_MACHINES_DIR)/*)
STATE_MACHINES_SRC_FILES := $(wildcard \
	$(STATE_MACHINES_DIR)/**/*.asl.json \
)
BUILD_SOURCES := $(TEMPLATE_FILE) \
	$(LAMBDA_LAYERS_SRC_FILES) \
	$(LAMBDA_FUNCTIONS_SRC_FILES) \
	$(STATE_MACHINES_SRC_FILES) \
	$(SAMCONFIG_FILE) \

SAM_BUILD_TOML_FILE := $(SAM_BUILD_DIR)/build.toml
$(SAM_BUILD_TOML_FILE): $(BUILD_SOURCES) | $(SAM_CMD)
	@echo '[INFO] sam building config env: [$(CONFIG_ENV)]'
	'$(SAM_CMD)' build --config-env '$(CONFIG_ENV)'

build: $(SAM_BUILD_TOML_FILE)
.PHONY: build

##########################################################################
# package
##########################################################################
PACKAGE_OUT_FILE := $(OUT_DIR)/template-packaged.yaml
$(PACKAGE_OUT_FILE): $(SAM_BUILD_TOML_FILE) | $(OUT_DIR) $(SAM_CMD)
	@echo '[INFO] sam packaging config env: [$(CONFIG_ENV)]'
	'$(SAM_CMD)' package \
		--config-env '$(CONFIG_ENV)' \
		--output-template-file '$(PACKAGE_OUT_FILE)'

package: $(PACKAGE_OUT_FILE)
.PHONY: package

##########################################################################
# publish
##########################################################################
PUBLISH_OUT_FILE := $(OUT_DIR)/sam-publish.txt
$(PUBLISH_OUT_FILE): $(PACKAGE_OUT_FILE) | $(OUT_DIR) $(SAM_CMD)
	@echo '[INFO] sam publishing config env: [$(CONFIG_ENV)]'
	'$(SAM_CMD)' publish \
		--debug \
		--config-env '$(CONFIG_ENV)' \
		--template '$(PACKAGE_OUT_FILE)' \
	| tee '$(@)'

publish: $(PUBLISH_OUT_FILE)
.PHONY: publish

##########################################################################
# deploy
##########################################################################
DEPLOY_OUT_FILE := $(OUT_DIR)/sam-deploy.txt
$(DEPLOY_OUT_FILE): $(SAM_BUILD_TOML_FILE) | $(OUT_DIR) $(SAM_CMD)
	@rm -f '$(DELETE_STACK_OUT_FILE)'
	@echo '[INFO] sam deploying config env: [$(CONFIG_ENV)]'
	'$(SAM_CMD)' deploy --config-env '$(CONFIG_ENV)' | tee '$(@)'

deploy: $(DEPLOY_OUT_FILE)
.PHONY: deploy

##########################################################################
# delete stack
##########################################################################
DELETE_STACK_OUT_FILE := $(OUT_DIR)/cfn-delete.txt
$(DELETE_STACK_OUT_FILE): $(SAMCONFIG_FILE) | $(OUT_DIR)
	@STACK_NAME=$$(python -c 'import toml; print( \
		toml.load("$(SAMCONFIG_FILE)")["$(CONFIG_ENV)"]["deploy"]["parameters"]["stack_name"] \
		)' \
	) ; \
	read -p "Do you want to delete the cloudformation stack: [$${STACK_NAME}]? " -r REPLY \
		&& [[ "$$REPLY" =~ ^[Yy]$$ ]] \
	&& echo "[INFO] deleting stack name: [$${STACK_NAME}]" \
	&& rm -f '$(DEPLOY_OUT_FILE)' \
	&& aws cloudformation delete-stack --stack-name "$${STACK_NAME}" \
	| tee '$(@)'

delete-stack: $(DELETE_STACK_OUT_FILE)
.PHONY: delete-stack

##########################################################################
# tests
##########################################################################

####
# local invoke
####
TESTS_DIR := tests
EVENTS_DIR := $(TESTS_DIR)/events

# build dynamic targets for sam local invoke
# each lambda function should have a corresponding invoke-local-% target
SAM_INVOKE_TARGETS := $(patsubst \
	$(LAMBDA_FUNCTIONS_DIR)/%, \
	local-invoke-%, \
	$(LAMBDA_FUNCTIONS) \
)
.PHONY: $(SAM_INVOKE_TARGETS)
$(SAM_INVOKE_TARGETS): build

ifdef DEBUGGER
DEBUG_PORT ?= 5678
export LOCAL_INVOKE_DEBUG_ARGS ?= --debug-port $(DEBUG_PORT) \
	--debug-args '-m debugpy --listen 0.0.0.0:$(DEBUG_PORT) --wait-for-client'
else
export LOCAL_INVOKE_DEBUG_ARGS ?= \

endif

# Invoke the default event associated with the lambda function
# for each lambda function, there should be a corresponding
# <CONFIG_ENV>.json file under the tests/events/<lambda_function_dir> directory
# where <lambda_function_dir> matches the directory name under
# src/lambda_functions. For example:
#
# make local-invoke-<lambda_function_dir>
#
# You may override the event file by setting the EVENT_FILE environmental
# variable:
# EVENT_FILE=myevent.json make local-invoke-<lambda_function_dir>
#
# The Lambda functions are invoked using environment variables from the file
# under tests/events/<CONFIG_ENV>-env-vars.json. This passes the --env-vars
# parameter to `sam local invoke`. See:
# https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-using-invoke.html#serverless-sam-cli-using-invoke-environment-file
# You can override the file by setting the ENV_VARS_FILE environmental variable:
#
# EVENT_VARS_FILE=my-env-vars.json make local-invoke-<lambda_function_dir>
#
# It parses out the logical resource name from the build.toml file
# For example, to invoke the src/lambda_functions/incoming_process use:
# make local-invoke-incoming_process
#
# To debug inside a Lambda function put debugpy in the function requirements.txt
# under the funtion directory. Set the DEBUGGER environmental variable when
# calling local invoke VS Code setup a launch task to attach to the debugger:
#        {
#            "name": "Debug SAM Lambda debugpy attach",
#            "type": "python",
#            "request": "attach",
#            "port": 5678,
#            "host": "localhost",
#            "pathMappings": [
#                {
#                    "localRoot": "${workspaceFolder}/${relativeFileDirname}",
#                    "remoteRoot": "/var/task"
#                }
#            ],
#        }
#
# To debug the incoming_process function use:
# DEBUGGER=true make local-invoke-incoming_process
$(SAM_INVOKE_TARGETS): local-invoke-%: $(LAMBDA_FUNCTIONS_DIR)/% | $(OUT_DIR) $(SAM_CMD)
	@FUNCTION_LOGICAL_ID=$$( \
	'$(VIRTUALENV_BIN_DIR)/python' -c 'import toml; \
	f_defs = ( \
	    toml.load("$(SAM_BUILD_TOML_FILE)") \
	    .get("function_build_definitions") \
	); \
	print( \
	    [f_defs[f]["functions"][0] \
	    for f in f_defs \
	    if f_defs[f]["codeuri"].endswith("/$(*)")] \
	    [0] \
	);' \
	) || { \
		echo -n "[ERROR] failed to parse sam build toml file. "; >&2 \
		echo -n "Check that you have sourced the python virtual env and "; >&2 \
		echo -n "run the command: "; >&2 \
		echo "[pip install -r $(PYTHON_REQUIREMENTS_DIR)/requirements-dev.txt]"; >&2 \
		exit 1; \
	} && \
	EVENT_FILE="$${EVENT_FILE:-$(EVENTS_DIR)/$(*)/$(CONFIG_ENV).json}" && \
	ENV_VARS_FILE="$${ENV_VARS_FILE:-$(EVENTS_DIR)/$(CONFIG_ENV)-env-vars.json}" && \
	echo "[INFO] invoking target: [$(@)] function: [$${FUNCTION_LOGICAL_ID}] with event file: [$${EVENT_FILE}]" && \
	'$(SAM_CMD)' local invoke \
		--config-env '$(CONFIG_ENV)' \
		--event "$$EVENT_FILE" \
		--env-vars "$$ENV_VARS_FILE" \
		$(LOCAL_INVOKE_DEBUG_ARGS) \
		"$$FUNCTION_LOGICAL_ID" | \
		tee '$(OUT_DIR)/$(@).txt'
	@echo
	@tail '$(OUT_DIR)/$(@).txt' | grep -q -E '^{ *"errorMessage" *:.*"errorType" *:' && { \
		echo "[ERROR] Lambda local invoke returned an error" >&2;\
		exit 1; \
	} || true

test-local-invoke-default: $(SAM_INVOKE_TARGETS)
.PHONY: test-local-invoke-default

test: test-local-invoke-default
.PHONY: test

##########################################################################
# lint
##########################################################################

###
# cfn-lint
###
CFN_LINT_OUT_FILE := $(OUT_DIR)/lint-cfn-lint.txt
$(CFN_LINT_OUT_FILE): $(TEMPLATE_FILE) | $(OUT_DIR)
	@echo '[INFO] running cfn-lint on template: [$(^)]'
	$(VIRTUALENV_BIN_DIR)/cfn-lint '$(^)' | tee '$(@)'

lint-cfn-lint: $(CFN_LINT_OUT_FILE)
.PHONY: lint-cfn-lint

###
# yamllint
###
YAMLLINT_OUT_FILE := $(OUT_DIR)/lint-yamllint.txt
$(YAMLLINT_OUT_FILE): $(TEMPLATE_FILE) | $(OUT_DIR)
	@echo '[INFO] running yamllint on template: [$(^)]'
	$(VIRTUALENV_BIN_DIR)/yamllint '$(^)' | tee '$(@)'

lint-yamllint: $(YAMLLINT_OUT_FILE)
.PHONY: lint-yamllint

###
# validate
###
VALIDATE_OUT_FILE := $(OUT_DIR)/lint-validate.txt
$(VALIDATE_OUT_FILE): $(TEMPLATE_FILE) | $(OUT_DIR)
	@echo '[INFO] running sam validate on config env: [$(CONFIG_ENV)]'
	$(VIRTUALENV_BIN_DIR)/sam validate --config-env '$(CONFIG_ENV)' | tee '$(@)'

lint-validate: $(VALIDATE_OUT_FILE)
.PHONY: lint-validate

###
# cfnnag
###
CFN_NAG_OUT_FILE := $(OUT_DIR)/lint-cfnnag.txt
$(CFN_NAG_OUT_FILE): $(TEMPLATE_FILE) | $(OUT_DIR)
	@echo '[INFO] running cfn_nag on template: [$(^)]'
	docker run -i --rm stelligent/cfn_nag /dev/stdin < '$(^)' | tee '$(@)'

lint-cfn_nag: $(CFN_NAG_OUT_FILE)
.PHONY: lint-cfn_nag

lint-cfn: lint-cfn-lint lint-yamllint lint-validate lint-cfn_nag
.PHONY: lint-cfn

###
# pylint
###

# TODO add Lamda Layers
PYLINT_DISABLE_IDS ?= W0511
PYTHON_LINTER_MAX_LINE_LENGTH ?= 100
LAMBDA_PYLINT_TARGETS := $(patsubst \
	$(LAMBDA_FUNCTIONS_DIR)/%, \
	$(OUT_DIR)/lint-pylint-%.txt, \
	$(LAMBDA_FUNCTIONS) \
)
$(LAMBDA_PYLINT_TARGETS): $(LAMBDA_FUNCTIONS_SRC_FILES)
$(LAMBDA_PYLINT_TARGETS): $(OUT_DIR)/lint-pylint-%.txt: $(LAMBDA_FUNCTIONS_DIR)/% | $(OUT_DIR)
	@echo '[INFO] running pylint on dir: [$(<)]'
	$(VIRTUALENV_BIN_DIR)/pylint \
		--max-line-length='$(PYTHON_LINTER_MAX_LINE_LENGTH)' \
		--disable="$(PYLINT_DISABLE_IDS)" \
		'$(<)' | \
		tee '$(@)'

lint-pylint: $(LAMBDA_PYLINT_TARGETS)
.PHONY: lint-pylint

###
# flake8
###
LAMBDA_FLAKE8_TARGETS := $(patsubst \
	$(LAMBDA_FUNCTIONS_DIR)/%, \
	$(OUT_DIR)/lint-flake8-%.txt, \
	$(LAMBDA_FUNCTIONS) \
)
$(LAMBDA_FLAKE8_TARGETS): $(LAMBDA_FUNCTIONS_SRC_FILES)
$(LAMBDA_FLAKE8_TARGETS): $(OUT_DIR)/lint-flake8-%.txt: $(LAMBDA_FUNCTIONS_DIR)/% | $(OUT_DIR)
	@echo '[INFO] running flake8 on dir: [$(<)]'
	$(VIRTUALENV_BIN_DIR)/flake8 \
		--max-line-length='$(PYTHON_LINTER_MAX_LINE_LENGTH)' \
		$(<) | \
		tee '$(@)'

lint-flake8: $(LAMBDA_FLAKE8_TARGETS)
.PHONY: lint-flake8

###
# mypy
###
LAMBDA_MYPY_TARGETS := $(patsubst \
	$(LAMBDA_FUNCTIONS_DIR)/%, \
	$(OUT_DIR)/lint-mypy-%.txt, \
	$(LAMBDA_FUNCTIONS) \
)
$(LAMBDA_MYPY_TARGETS): $(LAMBDA_FUNCTIONS_SRC_FILES)
$(LAMBDA_MYPY_TARGETS): $(OUT_DIR)/lint-mypy-%.txt: $(LAMBDA_FUNCTIONS_DIR)/% | $(OUT_DIR)
	@echo '[INFO] running mypy on dir: [$(<)]'
	$(VIRTUALENV_BIN_DIR)/mypy \
		$(<) | \
		tee '$(@)'

lint-mypy: $(LAMBDA_MYPY_TARGETS)
.PHONY: lint-mypy

###
# black
###
LAMBDA_BLACK_TARGETS := $(patsubst \
	$(LAMBDA_FUNCTIONS_DIR)/%, \
	$(OUT_DIR)/lint-black-%.txt, \
	$(LAMBDA_FUNCTIONS) \
)
$(LAMBDA_BLACK_TARGETS): $(LAMBDA_FUNCTIONS_SRC_FILES)
$(LAMBDA_BLACK_TARGETS): $(OUT_DIR)/lint-black-%.txt: $(LAMBDA_FUNCTIONS_DIR)/% | $(OUT_DIR)
	@echo '[INFO] running black on dir: [$(<)]'
	$(VIRTUALENV_BIN_DIR)/black \
		--check \
		--diff \
		--line-length='$(PYTHON_LINTER_MAX_LINE_LENGTH)' \
		$(<) | \
		tee '$(@)'

lint-black: $(LAMBDA_BLACK_TARGETS)
.PHONY: lint-black

###
# bandit
###
LAMBDA_BANDIT_TARGETS := $(patsubst \
	$(LAMBDA_FUNCTIONS_DIR)/%, \
	$(OUT_DIR)/lint-bandit-%.txt, \
	$(LAMBDA_FUNCTIONS) \
)
$(LAMBDA_BANDIT_TARGETS): $(LAMBDA_FUNCTIONS_SRC_FILES)
$(LAMBDA_BANDIT_TARGETS): $(OUT_DIR)/lint-bandit-%.txt: $(LAMBDA_FUNCTIONS_DIR)/% | $(OUT_DIR)
	@echo '[INFO] running bandit on dir: [$(<)]'
	$(VIRTUALENV_BIN_DIR)/bandit \
		--recursive \
		$(<) | \
		tee '$(@)'

lint-bandit: $(LAMBDA_BANDIT_TARGETS)
.PHONY: lint-bandit

lint-python: lint-pylint lint-flake8 lint-mypy lint-black lint-bandit
.PHONY: lint-python

###
# State Machine Lint
###
STATELINT_DIR ?= $(OUT_DIR)/statelint
STATELINT ?= $(STATELINT_DIR)/bin/statelint
$(STATELINT): | $(OUT_DIR)
	@echo "[INFO] installing statelint"
	-gem install statelint --install-dir '$(STATELINT_DIR)'

STATELINT_TARGETS := $(patsubst \
	$(STATE_MACHINES_DIR)/%, \
	$(OUT_DIR)/lint-statelint-%.txt, \
	$(STATE_MACHINES) \
)

$(STATELINT_TARGETS): $(STATE_MACHINES_SRC_FILES)
$(STATELINT_TARGETS): $(OUT_DIR)/lint-statelint-%.txt: $(STATE_MACHINES_DIR)/% | $(OUT_DIR)
	@echo "[INFO] Running statelint on file: [$(<)]"
	-@GEM_HOME='$(STATELINT_DIR)' '$(STATELINT)' '$(<)/state_machine.asl.json' | \
		tee '$(@)'

lint-state-machines: $(STATELINT_TARGETS)
.PHONY: lint-state-machines

###
# all linters
###
lint: lint-cfn lint-python lint-state-machines
.PHONY: lint

##########################################################################
# XXX TODO add help
##########################################################################
help:
.PHONY: help

##########################################################################
# clean
##########################################################################
clean-out-dir:
	-[ -d '$(OUT_DIR)' ] && rm -rf '$(OUT_DIR)/'*
.PHONY: clean-out-dir

clean-sam-dir:
	-[ -d '$(SAM_BUILD_DIR)' ] && rm -rf '$(SAM_BUILD_DIR)/'*
.PHONY: clean-sam-dir

# TODO clean docker container images

clean: clean-out-dir clean-sam-dir
.PHONY: clean
