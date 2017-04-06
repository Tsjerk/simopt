from setuptools import setup

setup(
    name='simopt',
    version='0.1',
    description='SIMple OPTion parser',
    long_description=open("README.md").read(),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
    ],
    keywords='simple option parser',
    url='http://github.com/Tsjerk/simopt',
    download_url='https://github.com/Tsjerk/simopt/archive/v0.1.tar.gz',
    author='Tsjerk A. Wassenaar',
    author_email='tsjerkw@gmail.com',
    license='MIT',
    py_modules=['simopt'],
    install_requires=[
    ],
    #      test_suite='nose.collector',
    #      tests_require=['nose', 'nose-cover3'],
    #      entry_points={
    #      },
    include_package_data=True,
    zip_safe=False
)



