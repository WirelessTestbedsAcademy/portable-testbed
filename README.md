# Portable-Testbed software

This repository contains software that is used in Portable Testbed to control Backbone Network:
	* Backbone Network Controller (BNC)
	* Backbone Network Agent
	* TMS-BNC Interface
	* Libs:
		* python-tc for Linux Traffic-Control subsystem configuration

## 1. Installation:
### 1.1 BN node:
```
pip install ./agent/
pip install ./python-tc/
```

### 1.2 Controller:
```
pip install ./controller/
pip install ./python-tc/
```

### 1.3 TMS:
```
pip install ./tms-bnc-interface/
```

## 2. Usage:

### 2.1 Agent:
```
python ./agent/bin/simple_agent --config=./agent/bin/config.yaml
```

### 2.2 Controller:
```
python ./controller/bin/simple_controller --config=./controller/bin/config.yaml
```

### 2.3 Simple TMS:
```
python ./tms-bnc-interface/bin/simple_tms
```

