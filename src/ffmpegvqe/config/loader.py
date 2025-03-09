#!/usr/bin/env python3
# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
"""Configuration loading functionality for FFmpeg video quality evaluations."""

import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from ffmpegvqe.encoding.encoder import get_versions
from ffmpegvqe.encoding.encoder import getprobe
from ffmpegvqe.utils.exceptions import VQEError
from ffmpegvqe.utils.file_operations import getfilehash
from ffmpegvqe.utils.yaml_handler import create_yaml_handler


def _get_default_patterns() -> list[dict[str, Any]]:
    """Get default encoding patterns.

    Returns:
        List of default encoding patterns.
    """
    return [
        {
            "codec": "libx264",
            "type": "CRF",
            "comments": "",
            "presets": ["medium"],
            "infile": {"option": ""},
            "outfile": {
                "options": [
                    "-crf 23",
                ],
            },
            "hwaccels": "",
        },
        {
            "codec": "libx265",
            "type": "CRF",
            "comments": "",
            "presets": ["medium"],
            "infile": {"option": ""},
            "outfile": {
                "options": [
                    "-crf 28",
                ],
            },
            "hwaccels": "",
        },
        {
            "codec": "libsvtav1",
            "type": "CRF",
            "comments": "",
            "presets": ["6"],
            "infile": {"option": ""},
            "outfile": {
                "options": [
                    "-crf 35",
                ],
            },
            "hwaccels": "",
        },
        {
            "codec": "h264_qsv",
            "type": "CQP",
            "comments": "",
            "presets": ["veryslow"],
            "infile": {"option": "-hwaccel qsv -c:v mpeg2_qsv"},
            "outfile": {
                "options": [
                    "-q:v 25",
                ],
            },
            "hwaccels": "-hwaccel_output_format qsv",
        },
        {
            "codec": "h264_qsv",
            "type": "ICQ",
            "comments": "",
            "presets": ["veryslow"],
            "infile": {"option": "-hwaccel qsv -c:v mpeg2_qsv"},
            "outfile": {
                "options": [
                    "-global_quality 25",
                ],
            },
            "hwaccels": "-hwaccel_output_format qsv",
        },
        {
            "codec": "h264_qsv",
            "type": "LA_ICQ",
            "comments": "",
            "presets": ["veryslow"],
            "infile": {"option": "-hwaccel qsv -c:v mpeg2_qsv"},
            "outfile": {
                "options": [
                    "-global_quality 25 -look_ahead 1",
                ],
            },
            "hwaccels": "-hwaccel_output_format qsv",
        },
        {
            "codec": "hevc_qsv",
            "type": "CQP",
            "comments": "",
            "presets": ["veryslow"],
            "infile": {"option": "-hwaccel qsv -c:v mpeg2_qsv"},
            "outfile": {
                "options": [
                    "-q:v 22",
                ],
            },
            "hwaccels": "-hwaccel_output_format qsv",
        },
        {
            "codec": "hevc_qsv",
            "type": "ICQ",
            "comments": "",
            "presets": ["veryslow"],
            "infile": {"option": "-hwaccel qsv -c:v mpeg2_qsv"},
            "outfile": {
                "options": [
                    "-global_quality 22",
                ],
            },
            "hwaccels": "-hwaccel_output_format qsv",
        },
        {
            "codec": "av1_qsv",
            "type": "CQP",
            "comments": "",
            "presets": ["veryslow"],
            "infile": {"option": "-hwaccel qsv -c:v mpeg2_qsv"},
            "outfile": {
                "options": [
                    "-q:v 35",
                ],
            },
            "hwaccels": "-hwaccel_output_format qsv",
        },
        {
            "codec": "av1_qsv",
            "type": "ICQ",
            "comments": "",
            "presets": ["veryslow"],
            "infile": {"option": "-hwaccel qsv -c:v mpeg2_qsv"},
            "outfile": {
                "options": [
                    "-global_quality 35",
                ],
            },
            "hwaccels": "-hwaccel_output_format qsv",
        },
    ]


def _filter_patterns(patterns: list[dict[str, Any]], args: object) -> list[dict[str, Any]]:
    """Filter patterns based on command line arguments.

    Args:
        patterns: List of encoding patterns.
        args: Command line arguments.

    Returns:
        Filtered list of encoding patterns.
    """
    filtered_patterns = patterns.copy()

    # argsオブジェクトにcodecとtype属性があるか確認
    if hasattr(args, "codec") and args.codec != "all":
        if hasattr(args, "type") and args.type == "all":
            filtered_patterns = [d for d in filtered_patterns if args.codec == d.get("codec")]
        elif hasattr(args, "type"):
            filtered_patterns = [
                d
                for d in filtered_patterns
                if args.codec == d.get("codec") and args.type == d.get("type")
            ]

    return filtered_patterns


def _get_default_references() -> list[dict[str, Any]]:
    """Get default reference files.

    Returns:
        List of default reference files.
    """
    return [
        {
            "name": "ABBB",
            "type": "Anime",
            "basefile": "./videos/source/ABBB_MPEG-2_1920x1080_30p.m2ts",
            "basehash": "f005791ab9cabdc4468317d5d58becf3eb6228a49c6fad09e0923685712af769",
        },
        {
            "name": "ASintel",
            "type": "Anime",
            "basefile": "./videos/source/ASintel_MPEG-2_1920x1080_30p.m2ts",
            "basehash": "8554804c935a382384eed9196ff88bd561767b6be1786aa4921087f265d92f3a",
        },
        {
            "name": "AToS",
            "type": "Anime",
            "basefile": "./videos/source/AToS_MPEG-2_1920x1080_30p.m2ts",
            "basehash": "ff6a0c366a3c631cf76d20c205cf505f964c9126551bf5bf10e8d99f9d04df52",
        },
        {
            "name": "NAir",
            "type": "Nature",
            "basefile": "./videos/source/NAir_MPEG-2_1920x1080_30p.m2ts",
            "basehash": "aec5612c556567df8cc3b37010c2850f709054293f1d5d0b96c68b349c2a97a2",
        },
        {
            "name": "NArmy",
            "type": "Nature",
            "basefile": "./videos/source/NArmy_MPEG-2_1920x1080_30p.m2ts",
            "basehash": "aef3503a79fcacf0e65e368416b0b0b85e54b8eb77e2613a4b750b59fb2b50d5",
        },
        {
            "name": "NNavy",
            "type": "Nature",
            "basefile": "./videos/source/NNavy_MPEG-2_1920x1080_30p.m2ts",
            "basehash": "52409e9400315916bb191dfafe4edd415204671ae00e2ddb447671f4850876cb",
        },
    ]


def _load_or_create_config(
    configfile: str,
    patterns: list[dict[str, Any]],
) -> tuple[dict[str, Any], bool]:
    """Load existing config or create a new one.

    Args:
        configfile: Path to the configuration file.
        patterns: List of encoding patterns.

    Returns:
        Tuple of (config, is_new_config).
    """
    yaml = create_yaml_handler()
    config_flag = False

    # configfile ディレクトリが存在しない場合は作成
    if not Path(configfile).parent.exists():
        Path.mkdir(Path(configfile).parent, parents=True)

    # settings.yml がある
    if Path(f"{configfile}").exists():
        print(f"{configfile} file found.")  # noqa: T201
        with Path(f"{configfile}").open("r") as file:
            configs = yaml.load(file)
    else:
        config_flag = True
        configs = {
            "configs": {
                "references": _get_default_references(),
                "datafile": "",
                "patterns": patterns,
            },
        }

    return configs, config_flag


def _validate_config(configs: dict[str, Any], patterns: list[dict[str, Any]]) -> dict[str, Any]:
    """Validate and fix configuration if needed.

    Args:
        configs: Configuration dictionary.
        patterns: List of encoding patterns.

    Returns:
        Validated configuration dictionary.
    """
    # __configsが辞書でない場合や必要なキーがない場合は、デフォルト値を使用
    if not isinstance(configs, dict) or "configs" not in configs:
        configs = {"configs": {"datafile": "", "references": [], "patterns": patterns}}
    elif not isinstance(configs["configs"], dict):
        configs["configs"] = {"datafile": "", "references": [], "patterns": patterns}

    # referencesの確認
    if "references" not in configs["configs"] or not isinstance(
        configs["configs"]["references"],
        list,
    ):
        configs["configs"]["references"] = []

    return configs


def _validate_references(configs: dict[str, Any]) -> None:
    """Validate reference files and their hashes.

    Args:
        configs: Configuration dictionary.

    Raises:
        VQEError: If reference file hash doesn't match.
    """
    for _index, _ref in enumerate(configs["configs"]["references"]):
        if not Path(
            f"{_ref['basefile'].replace(Path(_ref['basefile']).suffix, '_ffprobe.json', 1)}",
        ).exists():
            if configs["configs"]["references"][_index]["basehash"] != getfilehash(
                _ref["basefile"],
            ):
                __msg: str = f"Error: references name: {_ref['name']}, basehash not match."
                raise VQEError(__msg)
            print(f"References name: {_ref['name']}, basehash successfull.")  # noqa: T201
            getprobe(videofile=_ref["basefile"])


def _get_datafile_path(
    configs: dict[str, Any],
    configfile: str,
    args: object,
) -> tuple[str, list[dict[str, Any]]]:
    """Get datafile path and load existing encode configurations if available.

    Args:
        configs: Configuration dictionary.
        configfile: Path to the configuration file.
        args: Command line arguments.

    Returns:
        Tuple of (datafile_path, encode_configurations).
    """
    encode_cfg: list[dict[str, Any]] = []

    # datafileの取得
    if "datafile" in configs["configs"] and isinstance(configs["configs"]["datafile"], str):
        datafile = configs["configs"]["datafile"]
    else:
        datafile = ""

    # __datafile が設定されてなく、
    if datafile == "":
        datafile = f"{Path(configfile).parent}/data{str(uuid4())[24:]}.json"
        configs["configs"]["datafile"] = datafile
    elif Path(datafile).exists() and not getattr(args, "overwrite", False):
        # __datafile がある and --overwrite フラグがない
        with Path(datafile).open("r") as file:
            encode_cfg = json.load(file)

    return datafile, encode_cfg


# Helper class to group parameters for result template creation
class ResultTemplateParams:
    """Parameters for creating a result template."""

    def __init__(  # noqa: PLR0913
        self,
        pattern: dict[str, Any],
        preset: str,
        out_option: str,
        ref: dict[str, Any],
        args: object,
        distdir: Path,
    ) -> None:
        """Initialize parameters for result template creation.

        Args:
            pattern: Encoding pattern.
            preset: Preset to use.
            out_option: Output option.
            ref: Reference file.
            args: Command line arguments.
            distdir: Output directory.
        """
        self.pattern = pattern
        self.preset = preset
        self.out_option = out_option
        self.ref = ref
        self.args = args
        self.distdir = distdir


def _create_result_template(params: ResultTemplateParams) -> dict[str, Any]:
    """Create a result template for encoding.

    Args:
        params: Parameters for result template creation.

    Returns:
        Result template dictionary.
    """
    codec: str = params.pattern["codec"]
    type_: str = params.pattern["type"]
    comments: str = params.pattern["comments"]
    # argsオブジェクトにffmpeg_threads属性があるか確認
    threads: str = str(getattr(params.args, "ffmpeg_threads", 4))
    infile_opts: str = params.pattern["infile"]["option"]
    hwaccels: str = params.pattern["hwaccels"]

    out_option_hash: str = hashlib.sha256(
        str(
            [
                f"{codec}{type_}{params.preset}{params.out_option}",
                f"{threads}{hwaccels}{infile_opts}",
            ],
        ).encode(),
    ).hexdigest()

    out_id_hash: str = hashlib.sha256(
        str(f"{params.ref['basefile']}{params.ref['basehash']}{out_option_hash}").encode(),
    ).hexdigest()

    return {
        "id": f"{out_id_hash}",
        "id_opt": f"{out_option_hash}",
        "codec": codec,
        "type": type_,
        "comments": comments,
        "preset": params.preset,
        "threads": threads,
        "infile": {
            "name": params.ref["name"],
            "type": params.ref["type"],
            "filename": params.ref["basefile"],
            "duration": 0.0,
            "size_kbyte": 0.0,
            "option": infile_opts,
        },
        "outfile": {
            "filename": f"{params.distdir}/{out_id_hash[:12]}",
            "options": params.out_option,
            "hash": "",
            "bit_rate_kbs": 0.0,
            "duration": 0.0,
            "size_kbyte": 0.0,
            "stream": {
                "gop": 0,
                "has_b_frames": 0,
                "refs": 0,
                "frames": {"I": 0, "P": 0, "B": 0, "total": 0},
            },
        },
        "commandline": "",
        "hwaccels": hwaccels,
        "results": {
            "encode": {
                "second": 0.0,
                "time": "",
                "fps": 0,
                "speed": 0.0,
            },
            "compression_ratio_persent": 0.0,
            "probe": {
                "second": 0.0,
                "time": "",
            },
            "vmaf": {
                "second": 0.0,
                "time": "",
                "version": "",
                "commandline": "",
                "pooled_metrics": {
                    "float_ssim": {
                        "min": 0.0,
                        "max": 0.0,
                        "mean": 0.0,
                        "harmonic_mean": 0.0,
                    },
                    "vmaf": {
                        "min": 0.0,
                        "max": 0.0,
                        "mean": 0.0,
                        "harmonic_mean": 0.0,
                    },
                },
            },
        },
    }


def _generate_encoding_configs(
    configs: dict[str, Any],
    encode_cfg: list[dict[str, Any]],
    configfile: str,
    args: object,
) -> list[dict[str, Any]]:
    """Generate encoding configurations.

    Args:
        configs: Configuration dictionary.
        encode_cfg: Existing encoding configurations.
        configfile: Path to the configuration file.
        args: Command line arguments.

    Returns:
        List of encoding configurations.
    """
    distdir: Path = Path(f"./videos/dist/{Path(configfile).name.replace('.yml', '')}")
    existing_encodes = {encode["id"]: encode for encode in encode_cfg}
    results_list = list(encode_cfg)

    for pattern in configs["configs"]["patterns"]:
        presets: list[str] = pattern["presets"]
        for preset in presets:
            if not isinstance(pattern["outfile"]["options"], list):
                msg = f"outfile.options is must list[str] : {pattern['outfile']['options']}"
                raise VQEError(msg)

            for out_option in pattern["outfile"]["options"]:
                for ref in configs["configs"]["references"]:
                    params = ResultTemplateParams(
                        pattern=pattern,
                        preset=preset,
                        out_option=out_option,
                        ref=ref,
                        args=args,
                        distdir=distdir,
                    )
                    result_template = _create_result_template(params)

                    # 既存の encodes と比較して削除または追加
                    if result_template["id"] not in existing_encodes:
                        results_list.append(result_template)
                        print(  # noqa: T201
                            "encode new ...",
                            f"basefile: {ref['name']:12}",
                            f"preset: {result_template['preset']:8}",
                            f"codec: {result_template['codec']:12}",
                            f"type: {result_template['type']:24}",
                            f"options: {result_template['outfile']['options']}",
                        )

    return results_list


def _add_environment_info(configs: dict[str, Any], configfile: str) -> dict[str, Any]:
    """Add environment information to configuration.

    Args:
        configs: Configuration dictionary.
        configfile: Path to the configuration file.

    Returns:
        Updated configuration dictionary.
    """
    # テスト時にはget_versionsをスキップ
    if configfile != "test_config.yml":
        configs["configs"]["environment"] = get_versions(configfile=configfile)
    else:
        configs["configs"]["environment"] = {
            "ffmpege": {
                "program_version": "test_version",
                "library_versions": [],
            },
            "packages": {},
        }

    return configs


# Helper class to group parameters for save configs
class SaveConfigsParams:
    """Parameters for saving configurations."""

    def __init__(  # noqa: PLR0913
        self,
        configs: dict[str, Any],
        results_list: list[dict[str, Any]],
        configfile: str,
        datafile: str,
        config_flag: bool,  # noqa: FBT001
        existing_encodes: dict[str, dict[str, Any]],
    ) -> None:
        """Initialize parameters for saving configurations.

        Args:
            configs: Configuration dictionary.
            results_list: List of encoding configurations.
            configfile: Path to the configuration file.
            datafile: Path to the data file.
            config_flag: Whether this is a new configuration.
            existing_encodes: Dictionary of existing encoding configurations.
        """
        self.configs = configs
        self.results_list = results_list
        self.configfile = configfile
        self.datafile = datafile
        self.config_flag = config_flag
        self.existing_encodes = existing_encodes


def _save_configs(params: SaveConfigsParams) -> None:
    """Save configurations to files.

    Args:
        params: Parameters for saving configurations.
    """
    yaml = create_yaml_handler()

    print(f"\n\n{len(params.results_list)} pattern generate.\n\n")  # noqa: T201
    with Path(params.configfile).open("w") as file:
        yaml.dump(params.configs, file)

    if len(params.existing_encodes) == len(params.results_list):
        print(f"Exitst {params.datafile} no updated.")  # noqa: T201
    elif params.config_flag is True:
        print(f"Create datafile is {params.datafile} write.")  # noqa: T201
        with Path(params.datafile).open("w") as file:
            json.dump([], file)
    else:
        print(f"{len(params.results_list)} pattern is {params.datafile} write.")  # noqa: T201
        with Path(params.datafile).open("w") as file:
            json.dump(params.results_list, file)


def load_config(configfile: str, args: object) -> dict[str, Any]:
    """Load configuration from a YAML file.

    Loads configuration settings from a YAML file, validates reference files,
    and generates encoding configurations based on patterns and references.

    Args:
        configfile: Path to the configuration file.
        args: Command line arguments.

    Returns:
        Dictionary containing configuration settings and data file path.

    Raises:
        VQEError: If there are issues with the configuration.
    """
    # Get default patterns and filter based on args
    patterns = _get_default_patterns()
    patterns = _filter_patterns(patterns, args)

    # Load or create configuration
    configs, config_flag = _load_or_create_config(configfile, patterns)

    # Validate configuration
    configs = _validate_config(configs, patterns)

    # Validate reference files
    _validate_references(configs)

    # Get datafile path and load existing encode configurations
    datafile, encode_cfg = _get_datafile_path(configs, configfile, args)

    # Generate encoding configurations
    existing_encodes = {encode["id"]: encode for encode in encode_cfg}
    results_list = _generate_encoding_configs(configs, encode_cfg, configfile, args)

    # Add environment information
    configs = _add_environment_info(configs, configfile)

    # Save configurations
    save_params = SaveConfigsParams(
        configs=configs,
        results_list=results_list,
        configfile=configfile,
        datafile=datafile,
        config_flag=config_flag,
        existing_encodes=existing_encodes,
    )
    _save_configs(save_params)

    return {
        "configs": configs["configs"],
        "datafile": datafile,
    }
