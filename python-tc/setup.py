from setuptools import setup, find_packages

def readme():
    with open('README.md') as f:
        return f.read()

setup(
    name='python-tc',
    version='0.1.0',
    packages=find_packages(),
    license='',
    author='Piotr Gawlowicz',
    author_email='gawlowicz@tkn.tu-berlin.de',
    description='Python traffic-control subsystem tool',
    long_description='Python traffic-control subsystem tool',
    keywords='traffic-control, tc',
    install_requires=['docopt', 'pyroute2', 'python-iptables', 'msgpack-python']
)
