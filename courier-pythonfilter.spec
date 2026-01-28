%define expect_egg_info %(%{__python3} -c "import distutils.command.install_egg_info" > /dev/null 2>&1 && echo 1 || echo 0)

%define courier_user    %(. /etc/profile.d/courier.sh ; courier-config | grep ^mailuser | cut -f2 -d=)
%define courier_group   %(. /etc/profile.d/courier.sh ; courier-config | grep ^mailgroup | cut -f2 -d=)
%define courier_libexec %(. /etc/profile.d/courier.sh ; courier-config | grep ^libexecdir | cut -f2 -d=)

Name:      courier-pythonfilter
Version:   3.0
Release:   1%{?dist}
Summary:   Python filtering architecture for the Courier MTA.

License:   GPL-3.0-or-later
Url:       https://github.com/gordonmessmer/courier-pythonfilter/
Source0:   %{name}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  python3-pytest

BuildRequires:  courier
Requires:       courier

%global _description %{expand:
Pythonfilter provides a framework for writing message filters in
Python, as well as a selection of common filters.}

%description %_description

%prep
%autosetup


%generate_buildrequires
%pyproject_buildrequires


%build
%pyproject_wheel


%install
%pyproject_install
mv $RPM_BUILD_ROOT%{python3_sitelib}/etc $RPM_BUILD_ROOT%{_sysconfdir}

%pyproject_save_files -l pythonfilter courier

mkdir -p $RPM_BUILD_ROOT%{_localstatedir}/lib/pythonfilter/quarantine

mkdir -p ${RPM_BUILD_ROOT}%{courier_libexec}/filters
ln -s %{_bindir}/pythonfilter ${RPM_BUILD_ROOT}%{courier_libexec}/filters


%check
# TODO: shorten socket_path = '%s/tests/spool/courier/allfilters/pythonfilter' % project_root in testfilter
#pytest


%files -f %{pyproject_files}
%doc README README.developers
%if %{expect_egg_info}
  %{python3_sitelib}/courier_pythonfilter-*-info
%endif
%{_bindir}/*
%config(noreplace) %{_sysconfdir}/*
%attr(0700,%{courier_user},%{courier_group}) %dir %{_localstatedir}/lib/pythonfilter
%attr(0700,%{courier_user},%{courier_group}) %dir %{_localstatedir}/lib/pythonfilter/quarantine
%{courier_libexec}/filters/pythonfilter
