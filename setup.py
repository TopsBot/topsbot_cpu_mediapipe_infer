from glob import glob

from setuptools import find_packages, setup

package_name = "topsbot_cpu_mediapipe_infer"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", glob("launch/*.py")),
        ("share/" + package_name + "/config", glob("config/*.yaml")),
        ("share/" + package_name + "/scripts", glob("scripts/*")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="TopsFuture",
    maintainer_email="developer@topsfuture.com",
    description="MediaPipe CPU inference (hands/pose/face_detection) for TopsBot",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "mediapipe_infer = topsbot_cpu_mediapipe_infer.mediapipe_infer_node:main",
        ],
    },
)
