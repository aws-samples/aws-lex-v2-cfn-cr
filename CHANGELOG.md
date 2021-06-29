# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2021-06-30
### Added
- Support for FallbackIntent

## [0.2.0] - 2021-06-29
### Added
- New example based on QnABot Reponse bots. This example shows how to deploy
  many bots from the same template and tests the concurrent bot build
  retry logic
### Changed
- The boto3 client now uses the "adaptive" retry mode to better handle
  throttles
- The default log level of the Custom Resource Lambda is now set to "DEBUG"
  for easier troubleshooting. You can optionally set it to "INFO" or any
  of the other supported values
### Fixed
- Handle bot build exceptions caused by concurrent build quotas
- Handle resource deletion when the resource creation is cancelled by the
  user or by ClouFormation due to an error before the botId has been
  returned. When that happens, CloudFormation does not have a botId to
  delete the bot. This fix uses the botName from resource properties to
  find the related botId

## [0.1.0] - 2021-06-24
### Added
- Initial release

[Unreleased]: https://github.com/aws-samples/aws-lex-v2-cfn-cr/compare/v0.3.0...develop
[0.3.0]: https://github.com/aws-samples/aws-lex-v2-cfn-cr/compare/v0.3.0...v0.3.0
[0.2.0]: https://github.com/aws-samples/aws-lex-v2-cfn-cr/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/aws-samples/aws-lex-v2-cfn-cr/releases/tag/v0.1.0