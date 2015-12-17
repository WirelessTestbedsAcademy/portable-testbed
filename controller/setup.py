from setuptools import setup, find_packages

def readme():
    with open('README.md') as f:
        return f.read()

setup(
    name='wishful_controller',
    version='0.1.0',
    packages=find_packages(),
    url='http://www.wishful-project.eu/software',
    license='',
    author='Piotr Gawlowicz',
    author_email='gawlowicz@tkn.tu-berlin.de',
    description='WiSHFUL Controller Implementation',
    long_description='Implementation of a wireless controller',
    keywords='wireless control',
    scripts=['bin/simple_controller'],
    install_requires=['docopt', 'pyzmq', 'msgpack-python', 'apscheduler', 'pyyaml']
)
