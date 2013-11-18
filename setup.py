from setuptools import setup, find_packages

setup(
    name='django-currency',
    version='0.0.8',
    description="simple currency handling for djagngo",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Framework :: Django",
        "Environment :: Web Environment",
    ],
    keywords='django, currency, money',
    author='42coffecups.com, Yaroslav Klyuyev (imposeren)',
    author_email='yaroslav.k@42cc.co',
    url='https://github.com/42cc/django-currency',
    packages=find_packages(exclude=['test_project']),
    install_requires=[],
    include_package_data=True,
    zip_safe=False,
)
