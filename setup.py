from setuptools import setup

with open('README.md', 'r') as fh:
    long_description = fh.read()

setup(
    name='cgrr',
    description='Classic Game Resource Reader simplifies parsing game resource files',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Tracy Poff',
    author_email='tracy.poff@gmail.com',
    url='https://github.com/sopoforic/cgrr',
    packages=['cgrr'],
    install_requires=['ply'],
    setup_requires=['setuptools_scm'],
    use_scm_version=True,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
