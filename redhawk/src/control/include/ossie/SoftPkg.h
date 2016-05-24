/*
 * This file is protected by Copyright. Please refer to the COPYRIGHT file 
 * distributed with this source distribution.
 * 
 * This file is part of REDHAWK core.
 * 
 * REDHAWK core is free software: you can redistribute it and/or modify it 
 * under the terms of the GNU Lesser General Public License as published by the 
 * Free Software Foundation, either version 3 of the License, or (at your 
 * option) any later version.
 * 
 * REDHAWK core is distributed in the hope that it will be useful, but WITHOUT 
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or 
 * FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License 
 * for more details.
 * 
 * You should have received a copy of the GNU Lesser General Public License 
 * along with this program.  If not, see http://www.gnu.org/licenses/.
 */

#ifndef __SOFTPKG_H__
#define __SOFTPKG_H__

#include <sstream>
#include <istream>
#include <vector>
#include <string>
#include <cstring>
#include <boost/shared_ptr.hpp>
#include "ossie/exceptions.h"
#include "ossie/ossieparser.h"
#include "ossie/componentProfile.h"

#include "PropertyRef.h"
#include "UsesDevice.h"

namespace ossie {

    class SoftPkg;
    class Properties;
    class ComponentDescriptor;

    class SPD {
        public:
        typedef std::pair<std::string, std::string> NameVersionPair;

        class SoftPkgRef : public DependencyRef {
            public:
                std::string localfile;
                ossie::optional_value<std::string> implref;

                virtual const std::string asString() const;
                virtual ~SoftPkgRef() {};

                const boost::shared_ptr<SoftPkg>& getReference() const
                {
                    return _softpkg;
                }

                void setReference(const boost::shared_ptr<SoftPkg>& softpkg)
                {
                    _softpkg = softpkg;
                }

            private:
                boost::shared_ptr<SoftPkg> _softpkg;
        };


        typedef std::vector< ossie::SPD::SoftPkgRef > SoftPkgDependencies;


        class Author {
            public:
                std::vector<std::string> name;
                ossie::optional_value<std::string> company;
                optional_value<std::string> webpage;
        };


        class Code {
            public:
                // Required
                std::string localfile;
                // Optional
                optional_value<std::string> type;
                optional_value<std::string> entrypoint;
                optional_value<unsigned long long> stacksize;
                optional_value<unsigned long long> priority;

                Code() :
                    localfile(""),
                    type(""),
                    entrypoint(),
                    stacksize((unsigned long long)0),
                    priority((unsigned long long)0)
                {}

                Code(const Code& other) :
                    localfile(other.localfile),
                    type(other.type),
                    entrypoint(other.entrypoint),
                    stacksize(other.stacksize),
                    priority(other.priority)
                {}

                Code& operator=(const Code& other)
                {
                    localfile = other.localfile;
                    type = other.type;
                    entrypoint = other.entrypoint;
                    stacksize = other.stacksize;
                    priority = other.priority;
                    return *this;
                }
        };

        class Implementation {
            public:
                // Fields that are used in the framework
                std::string implementationID;
                Code code;
                optional_value<std::string> prfFile;

                std::vector<NameVersionPair> osDeps;
                std::vector<std::string> processorDeps;
                std::vector<PropertyRef> dependencies;
                SoftPkgDependencies       softPkgDependencies;
                std::vector<UsesDevice> usesDevice;

                // Fields that are not used at runtime
                // and could be eliminated to save memory
                std::string humanLanguageName;
                NameVersionPair compiler;
                NameVersionPair prgLanguage;
                NameVersionPair runtime;

            public:
                const std::string& getID() const {
                    return implementationID;
                }

                const std::vector<std::string>& getProcessors() const {
                    return processorDeps;
                }

                // Technically, per the DTD a component can list more than one OS
                // dependency...but the specification indicates that dependencies
                // indicate an 'and' relationship instead of an 'or' relationship
                const std::vector<NameVersionPair>& getOsDeps() const {
                    return osDeps;
                }

                const char * getPRFFile() const {
                    if (prfFile.isSet()) {
                        return prfFile->c_str();
                    } else {
                        return 0;
                    }
                }

                const std::string& getCodeFile() const {
                    return code.localfile;
                }

                const char * getCodeType() const {
                    if (code.type.isSet()) {
                        return code.type->c_str();
                    } else {
                        return 0;
                    }
                }

                const char * getEntryPoint() const {
                    if (code.entrypoint.isSet()) {
                        return code.entrypoint->c_str();
                    } else {
                        return 0;
                    }
                }

                const std::vector<ossie::UsesDevice>& getUsesDevices() const {
                    return usesDevice;
                };

                const std::vector<PropertyRef>& getDependencies() const {
                    return dependencies;
                }
            
                const ossie::SPD::SoftPkgDependencies& getSoftPkgDependencies() const {
                    return softPkgDependencies;
                }
        };

    public:
        typedef std::vector< ossie::SPD::Implementation > Implementations;

            // SPD Members
        public:
            SPD() :
                type("sca_compliant")
            {
            }

            std::string id;
            std::string name;
            std::string type;
            optional_value<std::string> version;
            optional_value<std::string> title;
            optional_value<std::string> description;
            optional_value<std::string> properties;
            optional_value<std::string> descriptor;
            std::vector<Author> authors;
            Implementations  implementations;
            std::vector<UsesDevice> usesDevice;
    };

    class SoftPkg {
        public:
            SoftPkg() : _spd(0), _spdFile("")  {}

            SoftPkg(std::istream& input, const std::string& _spdFile) throw (ossie::parser_error);

            SoftPkg& operator=(SoftPkg other)
            {
                _spd = other._spd;
                _spdFile = other._spdFile;
                return *this;
            }

        public:
            void load(std::istream& input, const std::string& _spdFile) throw (ossie::parser_error);

            const std::string& getSoftPkgID() const {
                assert(_spd.get() != 0);
                return _spd->id;
            }

            const std::string& getName() const {
                assert(_spd.get() != 0);
                return _spd->name;
            }

            const std::string& getSoftPkgType() const {
                return _spd->type;
            }

            const char* getSoftPkgVersion() const {
                assert(_spd.get() != 0);
                if (_spd->version.isSet()) {
                    return _spd->version->c_str();
                } else {
                    return 0;
                }
            }

            const char* getSoftPkgTitle() const {
                assert(_spd.get() != 0);
                if (_spd->title.isSet()) {
                    return _spd->title->c_str();
                } else {
                    return 0;
                }
            }

            const char* getDescription() const {
                assert(_spd.get() != 0);
                if (_spd->description.isSet()) {
                    return _spd->description->c_str();
                } else {
                    return 0;
                }
            }

            const std::string& getSPDPath() const {
                return _spdPath;
            }

            const std::string& getSPDFile() const {
                return _spdFile;
            }

            const char* getPRFFile() const {
                assert(_spd.get() != 0);
                if (!_spd->properties.isSet()) {
                    return 0;
                } else {
                    return _spd->properties->c_str();
                }
            }

            const char* getSCDFile() const {
                assert(_spd.get() != 0);
                if (!_spd->descriptor.isSet()) {
                    return 0;
                } else {
                    return _spd->descriptor->c_str();
                }
            }

            const std::vector<ossie::SPD::Author>& getAuthors() const {
                assert(_spd.get() != 0);
                return _spd->authors;
            }

            const ossie::SPD::Implementations& getImplementations() const {
                assert(_spd.get() != 0);
                return _spd->implementations; 
            }

            const std::vector<ossie::UsesDevice>& getUsesDevices() const {
                assert(_spd.get() != 0);
                return _spd->usesDevice;
            };

            bool isScaCompliant() const {
                assert(_spd.get() != 0);
                // Assume compliant unless explicitly set to non-compliant
                return _spd->type != "sca_non_compliant";
            }
            
            const boost::shared_ptr<Properties>& getProperties()
            {
                return _properties;
            }

            void setProperties(const boost::shared_ptr<Properties>& properties)
            {
                _properties = properties;
            }

            const boost::shared_ptr<ComponentDescriptor>& getDescriptor()
            {
                return _descriptor;
            }

            void setDescriptor(const boost::shared_ptr<ComponentDescriptor>& descriptor)
            {
                _descriptor = descriptor;
            }

        protected:
            std::auto_ptr<SPD> _spd;
            boost::shared_ptr<Properties> _properties;
            boost::shared_ptr<ComponentDescriptor> _descriptor;
            std::string _spdFile;
            std::string _spdPath;
    };

    template< typename charT, typename Traits>
    std::basic_ostream<charT, Traits>& operator<<(std::basic_ostream<charT, Traits> &out, const SPD::Code& code)
    {
        out << "localfile: " << code.localfile << " type: " << code.type << " entrypoint: " << code.entrypoint;
        return out;
    }

}
#endif
