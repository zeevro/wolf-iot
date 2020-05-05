from setuptools import setup


setup(
    name='wolf_iot',
    version='0.0.1',
    url='https://github.com/zeevro/wolf_iot',
    download_url='https://github.com/zeevro/wolf_iot/archive/master.zip',
    author='Zeev Rotshtein',
    author_email='zeevro@gmail.com',
    maintainer='Zeev Rotshtein',
    maintainer_email='zeevro@gmail.com',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Framework :: Flask',
        'Programming Language :: Python :: 3',
        'Topic :: Home Automation',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
    ],
    license=None,
    description='A tool to generate TOTP code based using secrets from WinAuth',
    keywords=[
        'Google Assistant',
        'Google Home',
        'Smart Home',
        'Home Automation',
        'OAuth 2.0',
    ],
    zip_safe=True,
    package_dir={
        '': 'src',
    },
    packages=[
        'wolf_iot',
    ],
    install_requires=[
        'flask',
    ],
    entry_points=dict(
        console_scripts=[
            'wolf_iot_server = wolf_iot.app:main',
        ],
    ),
)