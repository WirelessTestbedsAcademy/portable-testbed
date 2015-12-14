from setuptools import setup, find_packages

def readme():
    with open('README.md') as f:
        return f.read()

setup(
    name='tms_bnc_interface',
    version='0.1.0',
    packages=find_packages(),
    url='http://www.wishful-project.eu/software',
    license='',
    author='Piotr Gawlowicz',
    author_email='gawlowicz@tkn.tu-berlin.de',
    description='TMS-BNC Interface Implementation',
    long_description='Implementation of a TMS-BNC Interface',
    keywords='wireless control',
    scripts=['bin/simple_tms'],
    install_requires=['docopt', 'pyzmq', 'msgpack-python','gevent']
)
